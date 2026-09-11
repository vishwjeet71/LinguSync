import { useNavigate } from "react-router-dom";

export default function ProjectCart({
    id,
    projectName
}) {

    return (
        <>
            <div>
                <h3>{projectName}</h3>
                <p>Created At:</p>
                <button onClick={() => navigate(`/projects/${id}`)}>
                    open project
                </button>
            </div>
        </>
    );

}