// Model cart
import { useState } from "react";
import ModelCart from "./ModelCart";

export default function ListModels({ modelsManifest }) {

    const em = modelsManifest.efficient;
    const pm = modelsManifest.performance;

    const [isDownloading, setIsDownloading] = useState(false);
    const downloadProps = { isDownloading, setIsDownloading };

    return (
        <>
            <div>
                <div>
                    {em && Object.keys(em).length > 0 ? (<><h2>Efficient Models</h2>
                        <ModelBlock blockDetail={em} {...downloadProps} /></>) : null}
                </div>
                <div>
                    {pm && Object.keys(pm).length > 0 ? (<><h2>Performance Models</h2>
                        <ModelBlock blockDetail={pm} {...downloadProps} /></>) : null}
                </div>
                <div>{isDownloading ? <DownloadingBar /> : null}</div>
            </div>
        </>
    )
}

function ModelBlock({ blockDetail, ...downloadProps }) {

    const stt = blockDetail?.stt;
    const mt = blockDetail?.mt;
    const tts = blockDetail?.tts;

    return (
        <>
            <h3>Speech To Text model</h3>
            {stt ? (<ModelCart modelDetails={stt} {...downloadProps} />) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}

            <h3>Machine Translation</h3>
            {mt ? (<ModelCart modelDetails={mt} {...downloadProps} />) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}

            <h3>Text to Speech</h3>
            {tts ? (<ModelCart modelDetails={tts} {...downloadProps} />) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}
        </>
    )
}

function DownloadingBar() {
    return (
        <>Downloading....</>
    )
}