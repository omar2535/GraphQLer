import express from 'express';
import { createServer } from 'http';
import cors from 'cors';
import { WebSocketServer } from 'ws';
import { useServer } from 'graphql-ws/lib/use/ws';
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { makeExecutableSchema } from '@graphql-tools/schema';
import bodyParser from 'body-parser';
import fs from 'fs';
import resolvers from './data/schema.js'; // Import resolvers from schema.js

const PORT = process.env.PORT || 4000;
const app = express();
app.use(cors());

// Create HTTP server
const httpServer = createServer(app);

// Create the WebSocket server for subscriptions
const wsServer = new WebSocketServer({
  server: httpServer,
  path: '/graphql',
});

// Read schema from file
const schemaString = fs.readFileSync('./data/schema.gql', 'utf-8');

// Create executable schema with imported resolvers
const schemaExecutable = makeExecutableSchema({ typeDefs: [schemaString], resolvers });

useServer({ schema: schemaExecutable }, wsServer);

const startApolloServer = async () => {
  const server = new ApolloServer({
    schema: schemaExecutable,
  });

  await server.start();

  // Use express middleware to handle Apollo Server
  app.use('/graphql', bodyParser.json(), expressMiddleware(server));

  httpServer.listen(PORT, () => {
    console.log(`> Server ready at http://localhost:${PORT}/graphql`);
    console.log(`> Subscriptions ready at ws://localhost:${PORT}/graphql`);
  });
};

startApolloServer();
