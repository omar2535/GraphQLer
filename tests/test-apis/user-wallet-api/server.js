import express from 'express';
import {ApolloServer} from 'apollo-server-express';
import {createServer} from 'http';
import cors from 'cors';
import schema from './data/schema.js';

const PORT = process.env.PORT || 4000;
const app = express();

app.use('*', cors());

const server = new ApolloServer({
    schema,
    playground: true,
})

server.applyMiddleware({app});

const httpServer = createServer(app);

server.installSubscriptionHandlers(httpServer);

httpServer.listen(PORT, () => {
  console.log(`> Server ready at http://localhost:${PORT}${server.graphqlPath}`);
  console.log(`> Subscriptions ready at ws://localhost:${PORT}${server.subscriptionsPath}`);
});
