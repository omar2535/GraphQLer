import fs from 'fs';
import {v4} from 'uuid';

import { makeExecutableSchema } from 'graphql-tools';

const uuid = v4;

const schemaString = fs.readFileSync('./data/schema.gql', 'utf-8');

var users = []
var transactions = []
var locations = []
var currencies = []
var wallets = []


function getUser(id) {
    return users.find((u) => u.id === id);
}

function getUsers() {
    return users;
}

function getTransaction(id) {
    return transactions.find((t) => t.id === id);
}

function getTransactions() {
    return transactions
}

function getLocation(id) {
    return locations.find((l) => l.id === id);
}

function getLocations() {
    return locations;
}

function getCurrency(id) {
    return currencies.find((c) => c.id === id)

}

function getCurrencies() {
    return currencies;

}

function getWallet(id) {
    return wallets.find((w) => w.id === id);

}

function getWallets() {
    return wallets;
}


function getCurrentRate(currencyID, walletID) {
    // TODO: get rate
    return 1.0;
}
function createLocation(lat, lng, name) {
    const location = {
        id: uuid(),
        lat: lat,
        lng: lng,
        name: name
    };

    locations.push(location);

    return location;
}

function createUser(firstName, lastName, description) {
    const user = {
        firstName: firstName,
        lastName: lastName,
        description: description,
        id: uuid(),
        wallets: [],
        friends: [],
    };

    users.push(user);

    return user;
}


function createCurrency(abbreviation, symbol, country) {
    const currency = {
        id: uuid(),
        abbreviation: abbreviation,
        symbol: symbol,
        country: country
    };
    currencies.push(currency);

    return currency

}

function createWallet(name, currencyID, userID) {
    const wallet = {
        id: uuid(),
        name: name,
        currency: currencyID,
        transactions: [],
        user: userID,
    };
    wallets.push(wallet);

    return wallet;
}

function createTransaction(amount, payerID, walletID, currencyID, description) {
    const transaction = {
        id: uuid(),
        amount: amount,
        rate: getCurrentRate(currencyID, walletID),
        payer: payerID,
        description: description,
        location: createLocation(),
        timestamp: Date.now().toString(),
        walletID: walletID
    };

    transactions.push(transaction);

    return transaction;
}

function updateUser(id, firstName, lastName, description) {
    let user = users.find((u) => u.id === id)
    if (user == null){

    }else{
        if (firstName != null) user.firstName = firstName;
        if (lastName != null) user.lastName = lastName;
        if (description != null)user.description = description;
    }
    return user;
}

function updateTransaction(id, amount, payerID, description) {
    let transaction = transactions.find((t) => t.id === id)
    if (transaction == null){

    }else{
        if (amount != null) transaction.amount = amount;
        if (payerID != null && users.find((u) => u.id === payerID) != null) transaction.payer = payerID;
        if (description != null)transaction.description = description;
    }
    return transaction;
}

function updateLocation(id, lat, lng, name) {
    let location = locations.find((l) => l.id === id)
    if (location == null){

    }else{
        if (lat != null) location.lat = lat;
        if (lng != null) location.lng = lng;
        if (name != null) location.name = name;
    }
    return location;
}

function updateCurrency(id, abbreviation, symbol, country) {
    let currency = currencies.find((c) => c.id === id)
    if (currency == null){

    }else{
        if (abbreviation != null) currency.abbreviation = abbreviation;
        if (symbol != null) currency.symbol = symbol;
        if (country != null)currency.country = country;
    }
    return currency;
}

function updateWallet(id, name) {
    let wallet = wallets.find((w) => w.id === id)
    if (wallet == null){

    }else{
        if (name != null) wallet.name = name;
    }
    return wallet;
}

function deleteUser(id) {
    let user = users.find((u) => u.id === id);
    if (user == null){

    }else{
        users = users.filter(function(value, index, arr){
            return value.id != id;
        })
    }
    return user;
}

function deleteTransaction(id) {
    let transaction = transactions.find((t) => t.id === id);
    if (transaction == null){

    }else{
        transactions = transactions.filter(function(value, index, arr){
            return value.id != id;
        })
    }
    return transaction;
}

function deleteLocation(id) {
    let location = locations.find((l) => l.id === id);
    if (location == null){

    }else{
        locations = locations.filter(function(value, index, arr){
            return value.id != id;
        })
    }
    return location;
}

function deleteCurrency(id) {
    let currency = currencies.find((c) => c.id === id);
    if (currency == null){

    }else{
        currencies = currencies.filter(function(value, index, arr){
            return value.id != id;
        })
    }
    return currency;
}

function deleteWallet(id) {
    let wallet = wallets.find((c) => c.id === id);
    if (wallet == null){

    }else{
        wallets = wallets.filter(function(value, index, arr){
            return value.id != id;
        })
    }
    return wallet;
}

function calculateBalance(wallet) {
    return 0;
}

const resolvers = {
    Query: {
        getUser: (root, { userID }) => {
            return getUser(userID);

        },
        getTransaction: (root, { transactionID }) => {
            return getTransaction(transactionID);

        },
        getLocation: (root, { locationID }) => {
            return getLocation(locationID);
        },
        getCurrency: (root, { currencyID }) => {
            return getCurrency(currencyID);
        },
        getWallet: (root, { walletID }) => {
            return getWallet(walletID);
        },
        getUsers: () => {
            return getUsers();
        },
        getWallets: () => {
            return getWallets();
        },
        getTransactions: () => {
            return getTransactions();
        },
        getLocations: () => {
            return getLocations();
        },
        getCurrencies: () => {
            return getCurrencies();
        },
        /*
        hero: (root, { episode }) => getHero(episode),
        character: (root, { id }) => getCharacter(id),
        human: (root, { id }) => getHuman(id),
        droid: (root, { id }) => getDroid(id),
        starship: (root, { id }) => getStarship(id),
        reviews: (root, { episode }) => getReviews(episode),
        search: (root, { text }) => {
            const re = new RegExp(text, 'i');

            const allData = [
                ...humans,
                ...droids,
                ...starships,
            ];

            return allData.filter((obj) => re.test(obj.name));
        },
        */
    },
    Mutation: {
        /*
        createReview: (root, { episode, review }) => {
            reviews[episode].push(review);
            review.episode = episode;
            pubsub.publish(ADDED_REVIEW_TOPIC, { reviewAdded: review });
            return review;
        },
        */

        createUser: (root, { firstName, lastName, description }) => {
            return createUser(firstName, lastName, description);
        },

        createTransaction: (root, { amount, payerID, walletID, currencyID, description }) => {
            return createTransaction(amount, payerID, walletID, currencyID, description);
        },
        createLocation: (root, { lat, lng, name }) => {
            return createLocation(lat, lng, name);
        },
        createCurrency: (root, { abbreviation, symbol, country }) => {
            return createCurrency(abbreviation, symbol, country);
        },
        createWallet: (root, {name, currencyID, userID }) => {
            return createWallet(name, currencyID, userID);
        },

        updateUser: (root, {userID, firstName, lastName, description }) => {
            return updateUser(userID, firstName, lastName, description);
        },
        updateTransaction: (root, {transactionID, amount, payerID, description}) => {
            return updateTransaction(transactionID, amount, payerID, description);

        },
        updateLocation: (root, {locationID, lat, lng, name}) => {
            return updateLocation(locationID, lat, lng, name);
        },
        updateCurrency: (root, {currencyID, abbreviation, symbol, country}) => {
            return updateCurrency(currencyID, abbreviation, symbol, country);
        },
        updateWallet: (root, {walletID, name}) => {
            return updateWallet(walletID, name);
        },

        deleteUser: (root, {userID}) => {
            return deleteUser(userID);
        },
        deleteTransaction: (root, {transactionID}) => {
            return deleteTransaction(transactionID);
        },
        deleteLocation: (root, {locationID}) => {
            return deleteLocation(locationID);
        },
        deleteCurrency: (root, {currencyID}) => {
            return deleteCurrency(currencyID);
        },
        deleteWallet: (root, {walletID}) => {
            return deleteWallet(walletID);
        },

    },
    /*
    Subscription: {
        reviewAdded: {
            subscribe: withFilter(
                () => pubsub.asyncIterator(ADDED_REVIEW_TOPIC),
                (payload, variables) => {
                    return (payload !== undefined) &&
                        ((variables.episode === undefined) || (payload.reviewAdded.episode === variables.episode));
                }
            ),
        },
    },
    */
    User: {
        friends: (root) => {
            return root.friends.map((userID) => getUser(userID));
        },
        wallets: (root) => {
            return root.wallets.map((walletID) => getWallet(walletID));
        }
    },
    
    Wallet: {
        currency: (root) => {
            return getCurrency(root.currency);
        },
        transactions: (root) => {
            return root.transactions.map((id) => {
                return getTransaction(id);
            })
        },
        user: (root) => {
            return getUser(root.user);
        },
        balance: (root) => {
            return calculateBalance(root);
        }
    },
    Transaction: {
        payer: (root) => {
            return getUser(root.payer);
        },
        location: (root) => {
            return getLocation(root.location);
        },
        wallet: (root) => {
            return getWallet(root.walletID);
        }
    },
    Currency: {
        rate: getCurrentRate
    }
}

/**
 * Finally, we construct our schema (whose starting query type is the query
 * type we defined above) and export it.
 */
const walletSchema = makeExecutableSchema({
    typeDefs: [schemaString],
    resolvers
});

export default walletSchema;