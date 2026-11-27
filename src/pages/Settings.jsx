import About from "../components/About";

export default function Settings() {
    return (
        <div>
            {/* About Section */}
            <About />

            {/* Settings Section */}
            <section id="settings">
                <h2>Settings</h2>

                {/* OS Section */}
                <section id="os">
                    <h3>Operating System</h3>

                    <p>OS Type: Linux / Windows</p>
                    <p>Architecture: 64 / 32 bit</p>

                    <p>RAM: -- GB</p>
                    <p>CPU: --</p>
                </section>

                {/* GPU Section */}
                <section id="gpu">
                    <h3>GPU Information</h3>

                    <p>GPU: GPU Name</p>

                    <p>Is Detected: Boolean Value</p>
                    <p>Is CUDA Supported: Boolean Value</p>
                    <p>VRAM: -- GB</p>
                </section>

                {/* Required Software */}
                <section id="requirements">
                    <h3>Required Software</h3>

                    <ul>
                        <li>Software Name: Status</li>
                        <li>Software Name: Status</li>
                        <li>Software Name: Status</li>
                    </ul>
                </section>
            </section>
        </div>
    );
}