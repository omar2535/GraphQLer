/**
 * injection-vulnerabilities-api
 *
 * Intentionally vulnerable GraphQL API demonstrating:
 *   - SQL injection  (searchPosts)
 *   - Stored XSS     (createPost / getPost)
 *   - Path traversal (readFile)
 *   - OS command injection (executeCommand)
 *
 * DO NOT deploy this outside of a local test environment.
 */

const { ApolloServer } = require("apollo-server-express");
const express = require("express");
const sqlite3 = require("sqlite3");
const { v4: uuidv4 } = require("uuid");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 4002;
const db = new sqlite3.Database(":memory:");

// ── Schema ────────────────────────────────────────────────────────────────────
const typeDefs = `
  type Post {
    id: ID!
    title: String!
    content: String!
    author: String!
  }

  type CommandResult {
    output: String!
  }

  type FileResult {
    content: String!
  }

  type Query {
    """Returns posts whose title matches the query string (SQL-injectable)"""
    searchPosts(query: String!): [Post!]!

    """Returns a single post by ID (XSS: content is reflected verbatim)"""
    getPost(id: ID!): Post

    """Reads a file at the given path (path traversal vulnerable)"""
    readFile(path: String!): FileResult!
  }

  type Mutation {
    """Creates a post - content is stored and reflected back without sanitisation (XSS)"""
    createPost(title: String!, content: String!, author: String!): Post!

    """Executes a shell command (OS command injection vulnerable)"""
    executeCommand(cmd: String!): CommandResult!
  }
`;

// ── Database initialisation ───────────────────────────────────────────────────
function initDb() {
  db.serialize(() => {
    db.run(
      `CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT NOT NULL
      )`
    );
    // Seed some posts so searches can return data
    const seed = [
      [uuidv4(), "Hello World", "Welcome to our blog!", "admin"],
      [uuidv4(), "GraphQL Tips", "Use fragments for reuse.", "alice"],
      [uuidv4(), "Security 101", "Always sanitise user input.", "bob"],
    ];
    const stmt = db.prepare("INSERT INTO posts VALUES (?, ?, ?, ?)");
    seed.forEach((row) => stmt.run(row));
    stmt.finalize();
  });
}

// ── Resolvers ─────────────────────────────────────────────────────────────────
const resolvers = {
  Query: {
    // VULNERABLE: user input is interpolated directly into the SQL query
    searchPosts: (_, { query }) => {
      return new Promise((resolve, reject) => {
        // Intentionally unsafe — no parameterised query
        const sql = `SELECT * FROM posts WHERE title LIKE '%${query}%' OR content LIKE '%${query}%'`;
        db.all(sql, (err, rows) => {
          if (err) {
            // Return the raw DB error message so the detector can find it
            reject(new Error(`Database error: ${err.message}`));
          } else {
            resolve(rows || []);
          }
        });
      });
    },

    // VULNERABLE: content is never HTML-encoded; it is serialised straight into
    // the JSON response body so the raw script tag appears in request_response.text
    getPost: (_, { id }) => {
      return new Promise((resolve, reject) => {
        db.get("SELECT * FROM posts WHERE id = ?", [id], (err, row) => {
          if (err) reject(new Error(err.message));
          else resolve(row || null);
        });
      });
    },

    // VULNERABLE: path is used directly — traversal to /etc/passwd is possible
    readFile: (_, { path: filePath }) => {
      try {
        const content = fs.readFileSync(filePath, "utf8");
        return { content };
      } catch (err) {
        // Expose the OS error message verbatim
        return { content: `Error: ${err.message}` };
      }
    },
  },

  Mutation: {
    // VULNERABLE: stores unsanitised content that is later reflected in getPost
    createPost: (_, { title, content, author }) => {
      return new Promise((resolve, reject) => {
        const id = uuidv4();
        db.run(
          "INSERT INTO posts VALUES (?, ?, ?, ?)",
          [id, title, content, author],
          (err) => {
            if (err) reject(new Error(err.message));
            else resolve({ id, title, content, author });
          }
        );
      });
    },

    // VULNERABLE: executes cmd directly via the shell
    executeCommand: (_, { cmd }) => {
      try {
        const output = execSync(cmd, { timeout: 3000 }).toString();
        return { output };
      } catch (err) {
        return { output: err.stdout ? err.stdout.toString() : err.message };
      }
    },
  },
};

// ── Server bootstrap ──────────────────────────────────────────────────────────
async function startServer() {
  initDb();

  const app = express();
  const server = new ApolloServer({
    typeDefs,
    resolvers,
    // Disable Apollo's default error masking so raw error messages reach the client
    formatError: (err) => ({ message: err.message, locations: err.locations, path: err.path }),
  });

  await server.start();
  server.applyMiddleware({ app });

  app.listen(PORT, () => {
    console.log(`> injection-vulnerabilities-api ready at http://localhost:${PORT}/graphql`);
  });
}

startServer().catch(console.error);
