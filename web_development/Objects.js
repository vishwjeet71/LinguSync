const name = "Vishwjeet";
const age = 20;

const student = {
    name,
    age,
    address: {
        city: "Akola",
        state: "Maharashtra",
    },
    introduce() {
        return `Hi, I'm ${student.name} from ${student.address.city}`
    },
};

const property = "age";
console.log(student[property]); 
console.log(student.introduce());