/**
 * api-security-api
 *
 * GraphQL API for testing API-level security detectors:
 *   - Introspection enabled (IntrospectionDetector)
 *   - Field suggestions enabled (FieldSuggestionsDetector)
 *   - Query deny-list bypassable via aliases (QueryDenyBypassDetector)
 *
 * The deny-list middleware blocks requests whose body contains certain
 * operation names (e.g. "adminUsers"), but the alias detector sends the same
 * query using a short alias ("s: adminUsers") which bypasses the name check.
 *
 * DO NOT deploy this outside of a local test environment.
 */

const { ApolloServer } = require("apollo-server-express");
const express = require("express");
const { v4: uuidv4 } = require("uuid");

const PORT = process.env.PORT || 4004;

// ── In-memory data ────────────────────────────────────────────────────────────
const users = [
  { id: uuidv4(), name: "Alice", email: "alice@example.com", role: "admin" },
  { id: uuidv4(), name: "Bob",   email: "bob@example.com",   role: "user"  },
];

const posts = [
  { id: uuidv4(), title: "Hello", body: "World", authorId: users[0].id },
];

// ── Schema ────────────────────────────────────────────────────────────────────
const typeDefs = `
  type User {
    id: ID!
    name: String!
    email: String!
    role: String!
  }

  type Post {
    id: ID!
    title: String!
    body: String!
    author: User!
  }

  type Query {
    """Lists all users (publicly accessible)"""
    getUsers: [User!]!

    """Gets a single user (publicly accessible)"""
    getUser(id: ID!): User

    """Lists posts"""
    getPosts: [Post!]!

    """Admin-only query — blocked by name in the deny-list middleware,
       but bypassable via GraphQL aliases (QueryDenyBypassDetector target)"""
    adminUsers: [User!]!
  }

  type Mutation {
    """Creates a new user"""
    createUser(name: String!, email: String!): User!

    """Deletes a user by ID"""
    deleteUser(id: ID!): User
  }
`;

// ── Resolvers ─────────────────────────────────────────────────────────────────
const resolvers = {
  Query: {
    getUsers: () => users,
    getUser: (_, { id }) => users.find((u) => u.id === id) || null,
    getPosts: () => posts,
    // This resolver works fine — it's the HTTP-level deny-list that blocks it by name
    adminUsers: () => users,
  },

  Mutation: {
    createUser: (_, { name, email }) => {
      const user = { id: uuidv4(), name, email, role: "user" };
      users.push(user);
      return user;
    },
    deleteUser: (_, { id }) => {
      const idx = users.findIndex((u) => u.id === id);
      if (idx === -1) return null;
      const [removed] = users.splice(idx, 1);
      return removed;
    },
  },

  Post: {
    author: (post) => users.find((u) => u.id === post.authorId),
  },
};

// ── Query deny-list middleware ─────────────────────────────────────────────────
// Blocks requests that reference the literal string "adminUsers" as an operation
// field, but does NOT inspect aliases — so `s: adminUsers { ... }` passes through.
function queryDenyListMiddleware(req, res, next) {
  const body = req.body;
  if (!body) return next();

  const query = (typeof body === "string" ? JSON.parse(body) : body).query || "";

  // Naive deny-list: block if the field name appears standalone (not as alias target)
  // This regex matches "adminUsers" only when it is NOT preceded by a colon+space
  // (i.e. it would block `adminUsers {` but pass `s: adminUsers {`)
  const blockPattern = /(?<!:\s{0,10})adminUsers/;
  if (blockPattern.test(query)) {
    return res.status(400).json({
      errors: [{ message: "Operation 'adminUsers' is not allowed." }],
    });
  }

  next();
}

// ── Server bootstrap ──────────────────────────────────────────────────────────
async function startServer() {
  const app = express();
  app.use(express.json());

  // Apply deny-list before Apollo handles the request
  app.use("/graphql", queryDenyListMiddleware);

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    // Introspection and field suggestions are ON by default in Apollo Server 3.
    // Leaving them at default ensures IntrospectionDetector and
    // FieldSuggestionsDetector can flag this API.
    introspection: true,
    formatError: (err) => ({ message: err.message, locations: err.locations, path: err.path }),
  });

  await server.start();
  server.applyMiddleware({ app });

  app.listen(PORT, () => {
    console.log(`> api-security-api ready at http://localhost:${PORT}/graphql`);
  });
}

startServer().catch(console.error);
