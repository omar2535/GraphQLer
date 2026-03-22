/**
 * ssrf-api
 *
 * Intentionally SSRF-vulnerable GraphQL API.
 *
 * Exposes resolvers that make outbound HTTP connections based on user-supplied
 * URLs and reflect raw connection errors back to the caller. This lets the
 * SSRFInjectionDetector find patterns such as "connection refused" or
 * "ECONNREFUSED" in the response.
 *
 * DO NOT deploy this outside of a local test environment.
 */

const { ApolloServer } = require("apollo-server-express");
const express = require("express");
const http = require("http");
const https = require("https");
const { URL } = require("url");

const PORT = process.env.PORT || 4003;

// ── Schema ────────────────────────────────────────────────────────────────────
const typeDefs = `
  type FetchResult {
    url: String!
    statusCode: Int
    body: String!
    error: String
  }

  type PingResult {
    url: String!
    reachable: Boolean!
    message: String!
  }

  type Webhook {
    id: ID!
    url: String!
    lastStatus: String!
  }

  type Query {
    """Fetches the given URL and returns its body or connection error (SSRF vulnerable)"""
    fetchUrl(url: String!): FetchResult!

    """Pings a URL to check reachability; connection errors are exposed (SSRF vulnerable)"""
    pingEndpoint(url: String!): PingResult!
  }

  type Mutation {
    """Registers a webhook URL and immediately tests it (SSRF vulnerable)"""
    registerWebhook(url: String!): Webhook!
  }
`;

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Makes an HTTP/HTTPS GET request to `rawUrl` and returns the body or the
 * raw Node.js error message on failure. Errors are intentionally not masked.
 */
function doGet(rawUrl) {
  return new Promise((resolve) => {
    let parsed;
    try {
      parsed = new URL(rawUrl);
    } catch (_) {
      return resolve({ statusCode: null, body: "", error: `Invalid URL: ${rawUrl}` });
    }

    const lib = parsed.protocol === "https:" ? https : http;
    const req = lib.get(rawUrl, { timeout: 3000 }, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => resolve({ statusCode: res.statusCode, body: data.slice(0, 500), error: null }));
    });

    req.on("error", (err) => {
      // Expose raw Node.js error (e.g. "connect ECONNREFUSED 127.0.0.1:3000")
      resolve({ statusCode: null, body: "", error: err.message });
    });

    req.on("timeout", () => {
      req.destroy();
      resolve({ statusCode: null, body: "", error: "Request timed out" });
    });
  });
}

// ── Resolvers ─────────────────────────────────────────────────────────────────
const resolvers = {
  Query: {
    // VULNERABLE: makes an outbound request to an attacker-controlled URL
    fetchUrl: async (_, { url }) => {
      const result = await doGet(url);
      return {
        url,
        statusCode: result.statusCode,
        body: result.body || "",
        error: result.error,
      };
    },

    // VULNERABLE: exposes whether an internal address is reachable + raw OS error
    pingEndpoint: async (_, { url }) => {
      const result = await doGet(url);
      if (result.error) {
        return { url, reachable: false, message: result.error };
      }
      return { url, reachable: true, message: `HTTP ${result.statusCode}` };
    },
  },

  Mutation: {
    // VULNERABLE: tests a user-supplied webhook URL via outbound request
    registerWebhook: async (_, { url }) => {
      const result = await doGet(url);
      const lastStatus = result.error ? `error: ${result.error}` : `HTTP ${result.statusCode}`;
      return { id: String(Date.now()), url, lastStatus };
    },
  },
};

// ── Server bootstrap ──────────────────────────────────────────────────────────
async function startServer() {
  const app = express();
  const server = new ApolloServer({
    typeDefs,
    resolvers,
    formatError: (err) => ({ message: err.message, locations: err.locations, path: err.path }),
  });

  await server.start();
  server.applyMiddleware({ app });

  app.listen(PORT, () => {
    console.log(`> ssrf-api ready at http://localhost:${PORT}/graphql`);
  });
}

startServer().catch(console.error);
