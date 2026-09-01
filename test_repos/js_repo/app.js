const express = require('express');
const app = express();

// Security issue: eval usage
function processUserInput(userData) {
    eval(userData);  // SECURITY ISSUE
    return "processed";
}

// Security issue: innerHTML assignment
function updateContent(userInput) {
    document.getElementById('content').innerHTML = userInput;  // XSS RISK
}

// Hardcoded secret
const API_KEY = "sk-1234567890abcdef";
const password = "super-secret-password";

// Console.log in production
console.log("Application started");

// Weak random
const token = Math.random().toString(36);

function calculateTotal(items) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        total += items[i].price * items[i].quantity;
    }
    return total;
}

function getUserData(userId) {
    const query = "SELECT * FROM users WHERE id = " + userId;  // SQL INJECTION
    return db.query(query);
}

module.exports = { calculateTotal, getUserData };