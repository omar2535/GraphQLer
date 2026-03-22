const {ApolloServer} = require("apollo-server-express");
const {v4} = require("uuid");
const express = require("express");
const sqlite3 = require('sqlite3');
const db = new sqlite3.Database("./data.db");

const typeDefs = `
type Restaurant {
    id: ID!
    name: String!
    description: String!
    menu: [MenuItem!]
    reviews: [Review!]
  }
  
  type MenuItem {
    id: ID!
    name: String!
    description: String!
    price: Float!
    restaurant: Restaurant!
  }
  
  type Review {
    id: ID!
    rating: Int!
    comment: String!
    user: User!
    restaurant: Restaurant!
  }
  
  type User {
    id: ID!
    username: String!
    email: String!
    orders: [Order]!
  }
  
  type Order {
    id: ID!
    user: User!
    restaurant: Restaurant!
    items: [OrderedItem!]!
    totalAmount: Float!
    status: OrderStatus!
  }
  
  type OrderedItem {
    menuItem: MenuItem!
    quantity: Int!
  }
  
  enum OrderStatus {
    PLACED
    PREPARING
    OUT_FOR_DELIVERY
    DELIVERED
    CANCELLED
  }
  
  input CreateUserInput {
    username: String!
    email: String!
  }

  input CreateRestaurantInput {
    name: String!
    description: String!
  }

  input CreateReviewInput {
    userId: ID!
    restaurantId: ID!
    rating: Int!
    comment: String!
  }

  input CreateOrderInput {
    userId: ID!
    restaurantId: ID!
    items: [OrderedItemInput!]!
  }
  
  type Query {
    restaurants: [Restaurant!]!
    restaurant(id: ID!): Restaurant
    menuItems(restaurantId: ID!): [MenuItem!]!
    user(id: ID!): User
    order(id: ID!): Order
  }
  
  type Mutation {
    createOrder(userId: ID!, restaurantId: ID!, items: [OrderedItemInput!]!): Order
    cancelOrder(id: ID!): Order
    createReview(userId: ID!, restaurantId: ID!, rating: Int!, comment: String!): Review
    createUser(input: CreateUserInput!): User
    createRestaurant(input: CreateRestaurantInput!): Restaurant
  }
  
  input OrderedItemInput {
    menuItemId: ID!
    quantity: Int!
  }
`

const sampleData = {
  restaurants: [
    {
      id: '1',
      name: 'Tasty Delights',
      description: 'A cozy restaurant with a variety of delicious dishes.',
      menu: [],
      reviews: []
    },
    {
      id: '2',
      name: 'Pizza Palace',
      description: 'The best place for pizza lovers!',
      menu: [],
      reviews: []
    },
    // Add more restaurants as needed
  ],
  menuItems: [
    {
      id: '101',
      name: 'Spaghetti Carbonara',
      description: 'Classic Italian pasta with eggs, cheese, pancetta, and black pepper.',
      price: 12.99,
    },
    {
      id: '102',
      name: 'Margherita Pizza',
      description: 'Simple and delicious pizza with tomato, mozzarella, and basil.',
      price: 10.99,
    },
    // Add more menu items as needed
  ],
  reviews: [
    {
      id: '201',
      rating: 5,
      comment: 'I loved the food and the service! Highly recommended.',
      userId: '301',
      restaurantId: '1',
    },
    {
      id: '202',
      rating: 4,
      comment: 'Pizza was great, but the waiting time was a bit long.',
      userId: '302',
      restaurantId: '2',
    },
    // Add more reviews as needed
  ],
  users: [
    {
      id: '301',
      username: 'john_doe',
      email: 'john@example.com',
    },
    {
      id: '302',
      username: 'jane_smith',
      email: 'jane@example.com',
    },
    // Add more users as needed
  ],
  orders: [
    {
      id: '401',
      userId: '301',
      restaurantId: '1',
      totalAmount: 25.99,
      status: 'DELIVERED',
    },
    {
      id: '402',
      userId: '302',
      restaurantId: '2',
      totalAmount: 15.99,
      status: 'CANCELLED',
    },
    // Add more orders as needed
  ],
  orderedItems: [
    {
      orderId: '401',
      menuItemId: '101',
      quantity: 2,
    },
    {
      orderId: '402',
      menuItemId: '102',
      quantity: 1,
    },
    // Add more ordered items as needed
  ],
};




const resolvers = {
  Query: {
    restaurants: () => {
      return new Promise((resolve, reject) => {
        const sql = `
          SELECT
            r.*,
            m.id AS menuItem_id,
            m.name AS menuItem_name,
            m.description AS menuItem_description,
            m.price AS menuItem_price,
            rev.id AS review_id,
            rev.rating AS review_rating,
            rev.comment AS review_comment,
            rev.userId AS review_userId
          FROM restaurants r
          LEFT JOIN menuItems m ON r.id = m.restaurantId
          LEFT JOIN reviews rev ON r.id = rev.restaurantId
        `

        db.all(sql, [], (err, rows) => {
          if (err) reject(err);

          const restaurants = [];
          const restaurantMap = {};

          rows.forEach(row => {
            if (!restaurantMap[row.id]) {
              // current restaurant is not pushed into restaurants
              const restaurant = {
                id: row.id,
                name: row.name,
                description: row.description,
                menu: [],
                reviews: []
              };

              restaurant.push(restaurant);
              restaurantMap[row.id] = restaurant;
            }

            // Add menu items to restaurant;
            if (row.menuItem_id && !restaurantMap[row.id].menu.some(menuItem => menuItem.id === row.menuItem_id)) {
              const menuItem = {
                id: row.menuItem_id,
                name: row.menuItem_name,
                description: row.menuItem_description,
                price: row.menuItem_price,
                restaurant: {
                  
                }
              }
            }
          });
          
          resolve(restaurants);
        });


      });
      
    },
    restaurant: (_, { id }) => sampleData.restaurants.find(restaurant => restaurant.id === id),
    menuItems: (_, { restaurantId }) => sampleData.menuItems, // You need to filter by restaurantId
    user: (_, { id }) => sampleData.users.find(user => user.id === id),
    order: (_, { id }) => sampleData.orders.find(order => order.id === id),
  },
  Mutation: {
    createOrder: (_, { userId, restaurantId, items }) => {
      // Implement logic to create an order and return the created order
      // Remember to update your data source

      const orderId = v4();

      const newOrder = {
        id: orderId,
        userId,
        restaurantId,
        status: "PLACED",
        items: [],
        totalAmount: 0,
      }
      const totalAmount = items.reduce((total, item) => {
        const menuItem = sampleData.menuItems.find(
          (menuItem) => menuItem.id === item.menuItemId
        );

        if (!menuItem) {
          throw new Error(`Menu item not found: ${item.menuItemId}`);
        }

        newOrder.items.push({
          menuItem: menuItem.id,
          quantity: item.quantity
        });

        return total + menuItem.price * item.quantity;
      });

      newOrder.totalAmount = totalAmount;
      sampleData.orders.push(newOrder);

      return newOrder;

    },
    cancelOrder: (_, { id }) => {
      // Implement logic to cancel an order and return the canceled order
      // Remember to update your data source

      const orderIndex = sampleData.orders.findIndex((order) => order.id === id);
      
      if (orderIndex == -1) {
        throw new Error(`Order not found with ID: ${id}`);
      }

      if (sampleData.orders[orderIndex].status === 'CANCELLED') {
        throw new Error(`Order with ID ${id} is already cancelled.`);
      }

      sampleData.orders[orderIndex].status = 'CANCELLED';
      
      return sampleData.orders[orderIndex];
    },
    createReview: (_, { userId, restaurantId, rating, comment }) => {
      const reviewId = v4();
      
      const newReview = {
        id: reviewId,
        userId,
        restaurantId,
        rating,
        comment,
      };

      sampleData.reviews.push(newReview);

      return newReview;
    },
    createUser: (_, { input }) => {
      const userId = v4();
      const newUser = {
        id: userId,
        username: input.username,
        email: input.email,
        orders: []
      };

      sampleData.users.push(newUser);

      return newUser;
    },

    createRestaurant: (_, { input }) => {
      const restaurantId = v4();

      const newRestaurant = {
        id: restaurantId,
        name: input.name,
        description: input.description,
        menu: [],
        reviews: []
      };

      sampleData.restaurants.push(newRestaurant);

      return newRestaurant;
    }

    
  },
  Restaurant: {
    // Define resolvers for the Restaurant type fields if needed
    menu: (restaurant) => {
      return sampleData.menuItems.filter((menuItem) => restaurant.menu.includes(menuItem.id));
    },
    reviews: (restaurant) => {
      return sampleData.reviews.filter((review) => restaurant.reviews.includes(review.id));
    }
  },
  MenuItem: {
    // Define resolvers for the MenuItem type fields if needed
    restaurant: (menuItem) => {
      return sampleData.restaurants.find(
        (restaurant) => restaurant.id === menuItem.restaurantId
      );
    }
  },
  Review: {
    // Define resolvers for the Review type fields if needed
    user: (review) => {
      return sampleData.users.find((user) => user.id === review.userId);
    },
    restaurant: (review) => {
      return sampleData.restaurants.find(
        (restaurant) => restaurant.id == review.restaurantId
      );
    } 
  },
  User: {
    // Define resolvers for the User type fields if needed
    orders: (user) => {
      return sampleData.orders.filter((order) => user.orders.includes(order.id));
    }
  },
  Order: {
    // Define resolvers for the Order type fields if needed

    user: (order) => {
      return sampleData.users.find((user) => user.id === order.userId);
    },
    restaurant: (order) => {
      return sampleData.restaurants.find((restaurant) => restaurant.id === order.restaurantId);
    },
    items: (order) => {
      return sampleData.orderedItems.filter((orderedItem) => orderedItem.orderId === order.id);
    }
  },
  OrderedItem: {
    menuItem: (orderedItem) => {
      return sampleData.menuItems.find(
        (menuItem) => menuItem.id === orderedItem.menuItemId
      );
    }
  }
};

const app = express();

const server = new ApolloServer({
  typeDefs,
  resolvers
});

async function startApolloServer() {
  await server.start();
  server.applyMiddleware({ app });

  const PORT = process.env.PORT || 4000;

  app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}/graphql`);
  })
}


startApolloServer();
