// Simple Greeting Function
function Hii(name){
    return `Hii ${name}`;
}
console.log("Output Of first function:", Hii('Vishwajit'));

// Product Calculation
function multiply(a, b) {
    return a * b;
}
console.log("Output of second function:", multiply(8,9));

// Function with Default Parameters
function greet(name="Guest") {
    console.log("Output of third function:",`Hii ${name}`);
}
greet();

// Returning a Value
function square(number) {
    return number * number;
}
const result = square(6);
console.log("Output of fourth function:", result);

// Function Without a Return Value
function sayHellow() {
    console.log("Hellow");
}
const value = sayHellow();
console.log(value);

// Storing a Function in a Variable
const myFunction = greet();
console.log("Output of sixth function:", myFunction);

 // Task 
function calculateArea(
    length, width = length
) {
    return length * width;
}
const rectangleArea = calculateArea(5, 10);
const squareArea = calculateArea(7);
console.log(`Square area: ${squareArea}`);
console.log(`Rectangle area: ${rectangleArea}`);

// Arrow Functions
const add = (a,b) => a + b;
const greet = name => `hello ${name}`;
const printMessage = () => console.log('welcome');
const calculateDiscount = (price, discount = 10) => {
    const finalPrice = price - (price * discount) / 100;
    return finalPrice;
}