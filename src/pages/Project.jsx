import { useParams } from "react-router-dom";

export default function Project() {
    
    const { id } = useParams();

    return (
        <div>
            <h2>Project id: {id} </h2>
            <p>Unable to fetch data. The backend endpoint has not been implemented yet.</p>
        </div>
    );
}