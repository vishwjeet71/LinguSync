import { useEffect, useState } from "react";
import { useProjectContext } from "../App";

export default function Projects() {

    const { portNumber, setDisplayMessage } = useProjectContext();
    const [projectsData, setProjectsData] = useState("");
    const [isFailed, setIsFailed] = useState(false);

    useEffect(() => {

        const fetchData = async () => {

            const response = await fetch(`http://localhost:${portNumber}/load_data`)
            const responseData = await response.json();

            if (response.ok) {

                console.log(responseData.CM);
                setProjectsData(responseData.UM.projects);

            } else {

                console.error(responseData.CM);
                setDisplayMessage(responseData.UM);
                setIsFailed(true);

            }
        }

        fetchData();

    }, []);

    if (isFailed) {
        return (
            <>
                <h3>Unable to Bring your Data!</h3>
            </>
        );
    }


    if (projectsData === "") {
        return (
            <>
                <h3>Loading your projects...</h3>
            </>
        )
    }

    if (projectsData && projectsData.length === 0) {

        return (
            <>
                <h3>You have no Projects!</h3>
                <p>Create A project</p>
            </>
        );

    }
}