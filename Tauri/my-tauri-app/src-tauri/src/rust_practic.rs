struct Project {
    id: u32,
    name: String,
    status: String,
}

// Function taking two numbers and returning sum
fn add_numbers(a: i32, b: i32) -> i32 {
    a + b
}

// Result function rejecting empty project name
fn validate_name(name: String) -> Result<String, String> {
    if name.trim().is_empty() {
        Err(String::from("Project name cannot be empty!"))
    } else {
        Ok(name)
    }
}

// Function demonstrating Borrowing with &
fn print_project_status(status: &str) {
    println!("Project Status: {}", status);
}

fn main() {
    // 1. Mutable variable
    let mut total_count = 0;
    total_count += 1;
    println!("Total Count: {}", total_count);

    // 2. Sum function call
    let sum = add_numbers(10, 20);
    println!("Sum: {}", sum);

    // 3 & 4. Struct & Vec<Project> with 2 projects
    let p1 = Project {
        id: 1,
        name: String::from("Tauri App"),
        status: String::from("Active"),
    };
    let p2 = Project {
        id: 2,
        name: String::from("FastAPI Backend"),
        status: String::from("Pending"),
    };
    let projects: Vec<Project> = vec![p1, p2];

    // 5. Option<String> containing project name
    let project_opt: Option<String> = Some(projects[0].name.clone());

    // 6. Result function validation execution
    match validate_name(String::from("My Desktop App")) {
        Ok(valid_name) => println!("Validated: {}", valid_name),
        Err(err) => println!("Error: {}", err),
    }

    // 7. Borrowing with & (passing read-only reference)
    print_project_status(&projects[0].status);
}