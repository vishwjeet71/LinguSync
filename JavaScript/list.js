//list 
const fruits = ['Apple', 'Mango', 'Orange'];
fruits[1] = 'Banana';
console.log(fruits);

const numbers = [1,2];
numbers.push(3); // adding element at the end
numbers.unshift(0); // adding element at the beggining

console.log('Full list:', numbers);

numbers.pop();
console.log("After applyinh pop:", numbers);
numbers.shift();
console.log("After applying shift:", numbers);
console.log("Length of array:", numbers.length);

// Nested Arrays
const matrix = [
    [1,2],
    [3,4]
];
console.log("Matrix:", matrix);

// Iterating Through Arrays
for (const fruit of fruits) {
    console.log(fruit);
};

// Task 
const Books = [
    {
        title: "The Alchemist",
        author: "Paulo Coelho",
        price: 399,

    },
    {
        title: "Atomic Habits",
        author: "James Clear",
        price: 499,
    },
    {
        title: "Rich Dad Poor Dad ",
        author: "Robert T. Kiyosaki",
        price: 350,
    },
];

// Oprations
Books.push(
    {
        title: "The Guide",
        author: "R.K. Narayan",
        price: 299,

    }
);
Books.shift()

console.log("Length:", Books.length);
console.log("title of the last books:", Books[Books.length -1].title);
console.log("author of the first books:", Books[0].author);

// printing books
for (const book of Books) {
    console.log(`${book.title} - ${book.author} - ₹${book.price}`);
}

// Array Methods and task
// map
const doubled = numbers.map((number) => number * 2);

console.log("Orignal:", numbers);
console.log("Doubled:", doubled);

const students = [
    { name: "Vishwjeet", marks: 85 },
    { name: "Rahul", marks: 72 },
    { name: "Anjali", marks: 91 }
];

const student_names = students.map((student) => student.name);
const incresedMarks = students.map((student) => ({name: student.name, marks: student.marks + 5,}));
const stringOnly = students.map((student) => `${student.name} scored ${student.marks} marks.`);

console.log(stringOnly)

// filter
const products = [
    { name: "Laptop", price: 65000, inStock: true },
    { name: "Mouse", price: 700, inStock: false },
    { name: "Keyboard", price: 2500, inStock: true },
    { name: "Monitor", price: 12000, inStock: true },
    { name: "Headphones", price: 1800, inStock: false }
];

const availableStock = products.filter((product) => product.inStock);
const premiumProducts = products.filter((product) => product.price >= 2000);
const premiumAndInstock =  products.filter((product) => product.price >= 2000 && product.inStock);

for (const product of premiumAndInstock) {
    console.log(product.name);
}

// find
const employees = [
    { id: 101, name: "Amit", department: "HR", salary: 40000 },
    { id: 102, name: "Neha", department: "IT", salary: 65000 },
    { id: 103, name: "Rohan", department: "Finance", salary: 55000 },
    { id: 104, name: "Priya", department: "IT", salary: 70000 }
];

console.log(employees.find((e) => e.id === 103));
console.log(employees.find((e) => e.salary > 60000));
console.log(employees.find((e) => e.id === 999));

// some
const orders = [
    { id: 1, delivered: true, amount: 1200 },
    { id: 2, delivered: true, amount: 800 },
    { id: 3, delivered: false, amount: 2500 },
    { id: 4, delivered: true, amount: 600 }
];

console.log(orders.some((order) => !order.delivered)); 
console.log(orders.some((order) => order.amount > 2000));
console.log(orders.some((order) => order.amount > 5000));

// every
const users = [
    { name: "Amit", active: true, salary: 45000 },
    { name: "Neha", active: true, salary: 62000 },
    { name: "Rohan", active: false, salary: 55000 },
    { name: "Priya", active: true, salary: 70000 }
];

console.log(users.every((user) => user.active));
console.log(users.every((user) => user.salary >= 40000));
console.log(users.every((user) => user.salary >= 60000));

// forEach
const tasks = [
    { title: "Learn JavaScript", completed: true },
    { title: "Build React App", completed: false },
    { title: "Learn Tauri", completed: false }
];

tasks.forEach((task) => {
    console.log(
        `${task.completed ? "✓" : "✗"} ${task.title}`
    );
});

// reduce
const expenses = [1200, 800, 500, 1500, 700];

const totalExpense = expenses.reduce((total, current) => total + current);
console.log(totalExpense)

const cart = [
    { name: "Laptop", price: 65000, quantity: 1 },
    { name: "Mouse", price: 700, quantity: 2 },
    { name: "Keyboard", price: 2500, quantity: 1 }
];

const finalPrize = cart.reduce((prize, item) => {
    return prize + item.price * item.quantity
}, 0)
console.log(finalPrize)