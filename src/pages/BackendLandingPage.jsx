import GettingBackendReady from "../components/GettingBackendReady";

export default function BackendLandingPage({
    setPortNumber, setBackendStatus
}) {

    return (
        <>
            <div>
                <GettingBackendReady
                    setPortNumber={setPortNumber}
                    setBackendStatus={setBackendStatus}
                />
            </div>
        </>
    );
}