/**
 * nosql-time-sql-api
 *
 * Intentionally vulnerable GraphQL API demonstrating:
 *   - NoSQL injection  (searchUsers — MongoDB-style operator injection)
 *   - Time-based SQL blind injection (timeSqlQuery — SLEEP / pg_sleep / WAITFOR)
 *
 * DO NOT deploy this outside of a local test environment.
 */

const { ApolloServer } = require("apollo-server-express");
const express = require("express");

const PORT = process.env.PORT || 4005;

// ── In-memory dataset ─────────────────────────────────────────────────────────
const USERS = [
  { id: "1", username: "alice",  email: "alice@example.com",  role: "admin"  },
  { id: "2", username: "bob",    email: "bob@example.com",    role: "user"   },
  { id: "3", username: "carol",  email: "carol@example.com",  role: "user"   },
];

// ── Schema ────────────────────────────────────────────────────────────────────
const typeDefs = `
  type User {
    id: ID!
    username: String!
    email: String!
    role: String!
  }

  type QueryResult {
    result: String!
    rowsAffected: Int!
  }

  type Query {
    """
    Search users by username. Vulnerable to NoSQL injection:
    the filter string is parsed as JSON and MongoDB-style operators
    ($gt, $ne, $regex, etc.) are applied directly — bypassing auth checks.
    """
    searchUsers(filter: String!): [User!]!

    """
    Execute a parameterised query. Vulnerable to time-based SQL blind injection:
    the query string is interpolated into a SQL template and executed without
    sanitisation, allowing SLEEP / pg_sleep / WAITFOR DELAY to pause the server.
    """
    timeSqlQuery(query: String!): QueryResult!
  }
`;

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Returns true when the parsed filter object contains any MongoDB operator. */
function hasMongoOperator(obj) {
  if (typeof obj !== "object" || obj === null) return false;
  for (const [key, val] of Object.entries(obj)) {
    if (key.startsWith("$")) return true;
    if (typeof val === "object" && hasMongoOperator(val)) return true;
  }
  return false;
}

/**
 * Synchronous sleep: blocks the event loop for `ms` milliseconds.
 * This simulates a database that executes a time-based SQL payload
 * (e.g., SELECT pg_sleep(3)) and hangs until the sleep finishes.
 *
 * Uses Atomics.wait on a SharedArrayBuffer to avoid a busy-wait loop
 * that would otherwise peg a CPU core during the sleep window.
 */
function sleepSync(ms) {
  const shared = new SharedArrayBuffer(4); // 4 bytes for one Int32
  const int32 = new Int32Array(shared);
  // Block the current thread for up to `ms` milliseconds while waiting on index 0.
  Atomics.wait(int32, 0, 0, ms);
}

const MAX_SLEEP_MS = 5000; // cap to avoid runaway test hangs

// ── Resolvers ─────────────────────────────────────────────────────────────────
const resolvers = {
  Query: {
    // VULNERABLE: NoSQL injection
    // When a MongoDB operator is present in the JSON filter, all users are returned
    // (simulating a MongoDB $gt / $ne operator that bypasses the intended username filter).
    // When the JSON is syntactically invalid, a MongoServerError is raised to mimic the
    // raw error messages MongoDB surfaces in misconfigured apps.
    searchUsers: (_, { filter }) => {
      let parsed;
      try {
        parsed = JSON.parse(filter);
      } catch (e) {
        // Malformed JSON that still contains $ chars → emit a MongoDB-style error
        if (filter.includes("$")) {
          throw new Error(
            `MongoServerError: unknown operator: ${filter.match(/\$\w+/)?.[0] ?? "$unknown"}`
          );
        }
        // Plain string filter — do a simple substring match
        return USERS.filter(
          (u) => u.username.includes(filter) || u.email.includes(filter)
        );
      }

      if (hasMongoOperator(parsed)) {
        // Operator injection detected — return all users (auth bypass)
        return USERS;
      }

      // Legitimate exact-match filter e.g. {"username":"alice"}
      return USERS.filter((u) => {
        return Object.entries(parsed).every(([k, v]) => u[k] === v);
      });
    },

    // VULNERABLE: time-based SQL blind injection
    // The query string is not sanitised. Any SLEEP(N), pg_sleep(N), or
    // WAITFOR DELAY 'H:M:S' pattern triggers a real server-side delay, simulating
    // the behaviour of a backend that passes unsanitised input to its SQL engine.
    timeSqlQuery: (_, { query }) => {
      // MySQL / MariaDB: SLEEP(N)
      const sleepMatch = query.match(/\bSLEEP\s*\(\s*(\d+(?:\.\d+)?)\s*\)/i);
      if (sleepMatch) {
        const ms = Math.min(parseFloat(sleepMatch[1]) * 1000, MAX_SLEEP_MS);
        sleepSync(ms);
        return { result: "query executed", rowsAffected: 0 };
      }

      // PostgreSQL: pg_sleep(N)
      const pgMatch = query.match(/\bpg_sleep\s*\(\s*(\d+(?:\.\d+)?)\s*\)/i);
      if (pgMatch) {
        const ms = Math.min(parseFloat(pgMatch[1]) * 1000, MAX_SLEEP_MS);
        sleepSync(ms);
        return { result: "query executed", rowsAffected: 0 };
      }

      // MSSQL: WAITFOR DELAY 'HH:MM:SS'
      const waitforMatch = query.match(
        /\bWAITFOR\s+DELAY\s+['"]\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*['"]/i
      );
      if (waitforMatch) {
        const ms = Math.min(
          (parseInt(waitforMatch[1]) * 3600 + parseInt(waitforMatch[2]) * 60 + parseInt(waitforMatch[3])) * 1000,
          MAX_SLEEP_MS
        );
        sleepSync(ms);
        return { result: "query executed", rowsAffected: 0 };
      }

      return { result: "query executed", rowsAffected: 1 };
    },
  },
};

// ── Server bootstrap ──────────────────────────────────────────────────────────
async function startServer() {
  const app = express();
  const server = new ApolloServer({
    typeDefs,
    resolvers,
    // Disable Apollo's error masking so raw MongoServerError messages reach the client
    formatError: (err) => ({
      message: err.message,
      locations: err.locations,
      path: err.path,
    }),
  });

  await server.start();
  server.applyMiddleware({ app });

  app.listen(PORT, () => {
    console.log(`> nosql-time-sql-api ready at http://localhost:${PORT}/graphql`);
  });
}

startServer().catch(console.error);
