const employee = {
    name: "Vishwjeet",
    company: {
        address: {
            city: "Akola"
        }
    },
    experience: 0
};

const guest = null;

// optional chaining,
console.log(employee?.company?.address?.city)
console.log(guest?.name)

// nullish coalescing,
console.log(employee?.experience ?? 5)
console.log(employee?.salary ?? 30000)