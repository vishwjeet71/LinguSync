import { useEffect, useState, useRef } from "react";
import { useProjectContext } from "../App";

export default function GettingBackendReady({
    setPortNumber, setBackendStatus
}) {

    const [isFailed, setIsFailed] = useState(false);
    const attempt = useRef(1);
    const { portNumber } = useProjectContext();

    useEffect(() => {

        setIsFailed(false);
        console.log(
            `Starting backend on port ${portNumber}`
        );

        async function startBackend() {

            try {

                // Start Side Cart.
                const response = await waitForBackend(attempt, portNumber);
                if (response) {

                    setBackendStatus(response);
                }
                console.log("Backend is ready!");

            } catch (err) {

                console.error(err)
                setIsFailed(true);
            }
        }

        startBackend();

    }, [portNumber]);

    if (isFailed) {
        return (
            <>
                <div>
                    <h3>Failed to connect to port {portNumber}</h3>
                    <button onClick={() => getRandomPortNumber(setPortNumber)}>Retry</button>
                </div>
            </>
        );
    }

    return (
        <> <h3>Connecting to backend server...</h3></>
    );
}

async function waitForBackend(attempt, portNumber, timeout = 30000) {
    const start = Date.now();

    while (Date.now() - start < timeout) {

        try {
            const response = await fetch(`http://localhost:${portNumber}/lingusync`);

            if (response.ok) {

                console.log(
                    `Backend connected on port ${portNumber}`
                );
                return true;
            }
        } catch {
            console.warn(
                `Backend not ready. Attempt ${attempt.current} failed.`
            );
        }
        attempt.current += 1;
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
    throw new Error("Backend did not become ready in time");
}

function getRandomPortNumber(setPortNumber) {
    // Generate port between 10000 and 60000
    const portNumber =
        Math.floor(Math.random() * 50000) + 10000;

    console.log(`Trying new port: ${portNumber}`);

    setPortNumber(String(portNumber));
}