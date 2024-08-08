import express from 'express';
import { ApolloServer } from 'apollo-server-express';
import { createServer } from 'http';
import cors from 'cors';
import { useServer } from 'graphql-ws/lib/use/ws';
import { ApolloServerPluginDrainHttpServer } from 'apollo-server-core';
import schema from './data/schema.js';
import { WebSocketServer } from 'ws';

const PORT = process.env.PORT || 4000;
const app = express();

app.use('*', cors());

const httpServer = createServer(app);

const startApolloServer = async () => {
  const server = new ApolloServer({
    schema,
    plugins: [ApolloServerPluginDrainHttpServer({ httpServer })],
  });

  await server.start();

  server.applyMiddleware({ app });

  const wsServer = new WebSocketServer({
    server: httpServer,
    path: server.graphqlPath,
  });

  useServer({ schema }, wsServer);

  httpServer.listen(PORT, () => {
    console.log(`> Server ready at http://localhost:${PORT}${server.graphqlPath}`);
    console.log(`> Subscriptions ready at ws://localhost:${PORT}${server.graphqlPath}`);
  });
};

startApolloServer();
