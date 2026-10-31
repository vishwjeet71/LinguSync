import { useNavigate } from "react-router-dom";

export default function Sidebar() {
    const navigate = useNavigate();

    return (
        <aside>
            <p>Side Bar</p>

            <button onClick={() => navigate("/")}>
                Home
            </button>

            <button onClick={() => navigate("/model")}>
                Models
            </button>

            <button onClick={() => navigate("/settings")}>
                Settings
            </button>
        </aside>
    );
}