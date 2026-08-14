import { Link } from "react-router-dom";

import Cart from "../components/cart";
import UserList from "../components/UserList"

function Dashboard() {
  return (
    <>
      <h1>Developer Workspace</h1>
        <Cart>
          <p>Hii</p>
        </Cart>
      <UserList/>
      <div>
        <Link to="/projects">
          <button>View Projects</button>
        </Link>
      </div>
    </>
  );
}

export default Dashboard;