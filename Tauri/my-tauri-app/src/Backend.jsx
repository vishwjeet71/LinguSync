import { useState, useEffect } from "react";
import { Command } from "@tauri-apps/plugin-shell";

export default function FastApiBackend() {
    const [isBackend, setIsBackend] = useState("Not Connected");
    const [backendProcess, setBackendProcess] = useState(null);

    const startBackend = async () => {
        try {
            setIsBackend("Connecting...");
            const cmd = Command.sidecar("binaries/backend");

            cmd.stdout.on('data', line => console.log(`Backend stdout: ${line}`));
            cmd.stderr.on('data', line => console.error(`Backend stderr: ${line}`));

            cmd.on('close', data => {
                console.warn(`Backend process exited with code: ${data.code}`);
                setIsBackend("Failed to Start / Crashed");
            });

            const child = await cmd.spawn();
            setBackendProcess(child);

            // Backend ko start hone ke liye 2 seconds ka time dein
            setTimeout(() => {
                checkBackend();
            }, 2000);

        } catch (error) {
            console.error("Failed to launch process:", error);
            setIsBackend("Failed to Start");
        }
    };

    const stopBackend = async () => {
        // Agar process reference hamare paas hai (Remote hai)
        if (backendProcess) {
            try {
                await backendProcess.kill();
                setBackendProcess(null);
                setIsBackend("Not Connected");
            } catch (error) {
                console.error("Failed to kill backend:", error);
            }
        }
        // Agar process reference null hai par backend connected hai (Remote kho gaya)
        else if (isBackend === "Connected") {
            try {
                // Direct FastAPI ko band hone ka order dein
                await fetch("http://127.0.0.1:8000/shutdown", { method: 'POST' });
                setIsBackend("Not Connected");
            } catch (error) {
                console.error("Failed to shutdown backend via API:", error);
                setIsBackend("Connection Refused");
            }
        }
    };

    const checkBackend = async () => {
        try {
            const response = await fetch("http://127.0.0.1:8000/health");
            if (response.ok) {
                setIsBackend("Connected");
            } else {
                setIsBackend("Error Response");
            }
        } catch (error) {
            setIsBackend("Connection Refused");
            console.error("Backend is offline:", error);
        }
    };

    useEffect(() => {
        checkBackend();
    }, []);

    return (
        <div>
            <h2>Status: {isBackend}</h2>

            <button
                onClick={startBackend}
                disabled={isBackend === "Connected" || isBackend === "Connecting..."}
            >
                Start Backend
            </button>

            <button
                onClick={stopBackend}
                disabled={isBackend !== "Connected"}
            >
                Stop Backend
            </button>

            <button onClick={checkBackend}>
                Check Status
            </button>
        </div>
    );
}