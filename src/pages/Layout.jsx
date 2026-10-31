import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar";

export default function Layout() {
    return (
        <div>
            <Sidebar />
            <main>
                <Outlet />
            </main>
        </div>
    );
}