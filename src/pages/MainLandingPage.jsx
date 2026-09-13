import Projects from "../components/Projects";

// Navigation
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Project from "./Project";

export default function MainLandingPage() {

    return (
        <>
            <BrowserRouter>
                <Routes>
                    <Route
                        path="/"
                        element={
                            <>
                                <h2>Welcome To LinguSync</h2>
                                <h3>Your Local Video Dubbing system</h3>
                                <Projects />
                            </>
                        }
                    />
                    <Route path="/projects/:id" element={<Project />} />
                </Routes>
            </BrowserRouter>
        </>
    );

}