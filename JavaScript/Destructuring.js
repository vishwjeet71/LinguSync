const employee = {
    id: 101,
    name: "Vishwjeet",
    department: "AI",
    salary: 70000,
    address: {
        city: "Akola",
        state: "Maharashtra"
    }
};

const skills = [
    "Python",
    "JavaScript",
    "React",
    "FastAPI"
];

const {name, department, salary: monthlySalary, address: {city}} = employee;
const {experience = 0} = employee;
const [primarySkill ,,frontendSkill] = skills;

console.log(name, department, monthlySalary, city, experience);
console.log(primarySkill, frontendSkill);

const frontend = [
    "HTML",
    "CSS",
    "JavaScript"
];

const backend = [
    "Python",
    "FastAPI"
];

const developer = {
    name: "Vishwjeet",
    city: "Akola",
    experience: 1
};

// Spread
const allSkills = [...frontend, ...backend];
const updatedDeveloper = {...developer, experience: 2};
// Rest
const [primarySkill, ...remainingSkills] = allSkills;
// Rest Parameters
function calculateTotal(...inputNumbers) {
    const totalSum = inputNumbers.reduce((sum, current) => sum + current, 0);
    return totalSum
}

console.log(calculateTotal(10, 20, 30, 40))