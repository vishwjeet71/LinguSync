import { useNavigate } from "react-router-dom";

export default function ProjectCart({
    id,
    projectName,
    created_at
}) {

    return (
        <>
            <div>
                <h3>{projectName}</h3>
                <p>Created At: {created_at}</p>
                <button onClick={() => navigate(`/projects/${id}`)}>
                    open project
                </button>
            </div>
        </>
    );

}