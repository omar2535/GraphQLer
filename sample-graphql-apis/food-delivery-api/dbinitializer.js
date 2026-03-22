const sqlite3 = require("sqlite3").verbose();
const fs = require("fs");

const dbFile = "./data.db";


const createRestaurantTableStmt = `
-- Restaurants table
CREATE TABLE restaurants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);
`


const createMenuItemsTableStmt =`
-- Menu items table
CREATE TABLE menuItems (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL,
    restaurantId TEXT,
    FOREIGN KEY(restaurantId) REFERENCES restaurants(id)
);
`

const createUsersTableStmt = `
-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL
);
`

const createReviewsTableStmt = `
-- Reviews table
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    rating INTEGER NOT NULL,
    comment TEXT,
    userId TEXT,
    restaurantId TEXT,
    FOREIGN KEY(userId) REFERENCES users(id),
    FOREIGN KEY(restaurantId) REFERENCES restaurants(id)
);
`

const createOrdersTableStmt = `
-- Orders table
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    totalAmount REAL NOT NULL,
    status TEXT NOT NULL,
    userId TEXT,
    restaurantId TEXT,
    FOREIGN KEY(userId) REFERENCES users(id),
    FOREIGN KEY(restaurantId) REFERENCES restaurants(id)
);
`

const createOrderedItemsTableStmt = `
-- Ordered items table
CREATE TABLE orderedItems (
    orderId TEXT,
    menuItemId TEXT,
    quantity INTEGER NOT NULL,
    FOREIGN KEY(orderId) REFERENCES orders(id),
    FOREIGN KEY(menuItemId) REFERENCES menuItems(id),
    PRIMARY KEY(orderId, menuItemId)
);
`

if (!fs.existsSync(dbFile)) {
    const db = new sqlite3.Database(dbFile);
    db.serialize(() => {
        db.run(createRestaurantTableStmt);
        db.run(createMenuItemsTableStmt);
        db.run(createUsersTableStmt);
        db.run(createReviewsTableStmt);
        db.run(createOrdersTableStmt);
        db.run(createOrderedItemsTableStmt);
        db.close((err) => {
            if (err) {
                console.error('Error closing the Db', err);
            } else {
                console.log('Db initialized');
            }
        });
    });
}   else {
    console.log("Db already existed.");
}
