// components
import Projects from "../components/Projects";

// Navigation
import { BrowserRouter, Routes, Route } from "react-router-dom";

// pages
import ModelsManagerPage from "./Models";
import Layout from "./Layout";
import Project from "./Project";
import Settings from "./Settings";

function Home() {
    return (
        <div>
            <h2>Welcome To LinguSync</h2>
            <h3>Your Local Video Dubbing System</h3>
            <Projects />
        </div>
    );
}

export default function MainLandingPage() {

    return (
        <>
            <BrowserRouter>
                <Routes>
                    <Route element={<Layout />}>
                        <Route path="/" element={<Home />} />
                        <Route path="/model" element={<ModelsManagerPage />} />
                        <Route path="/settings" element={<Settings />} />
                        <Route path="/projects/:id" element={<Project />} />
                    </Route>
                </Routes>
            </BrowserRouter>
        </>
    );

}