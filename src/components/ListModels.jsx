// Model cart
import { useState } from "react";
import ModelCart from "./ModelCart";

export default function ListModels({ modelsManifest, setNeedToRefresh }) {

    const em = modelsManifest.efficient;
    const pm = modelsManifest.performance;

    const [isDownloading, setIsDownloading] = useState(false);
    const downloadProps = { isDownloading, setIsDownloading };

    return (
        <>
            <div>
                <div>
                    {em && Object.keys(em).length > 0 ? (<><h2>Efficient Models</h2>
                        <ModelBlock blockDetail={em} setNeedToRefresh={setNeedToRefresh} {...downloadProps} /></>) : null}
                </div>
                <div>
                    {pm && Object.keys(pm).length > 0 ? (<><h2>Performance Models</h2>
                        <ModelBlock blockDetail={pm} setNeedToRefresh={setNeedToRefresh} {...downloadProps} /></>) : null}
                </div>
                <div>{isDownloading ? <DownloadingBar /> : null}</div>
            </div>
        </>
    )
}

function ModelBlock({ blockDetail, setNeedToRefresh, ...downloadProps }) {

    const stt = blockDetail?.stt;
    const mt = blockDetail?.mt;
    const tts = blockDetail?.tts;

    const [requestFile, setRequestFile] = useState("");

    return (
        <>
            {requestFile && (
                <FileRemovingWarrningPOPUP
                    requestFile={requestFile.fileName}
                    onConfirm={() => {
                        requestFile.resolve(true);
                        setRequestFile("");
                    }}
                    onCancel={() => {
                        requestFile.resolve(false);
                        setRequestFile("");
                    }}
                />
            )}
            <h3>Speech To Text model</h3>
            {stt ? (<ModelCart modelDetails={stt} setRequestFile={setRequestFile} setNeedToRefresh={setNeedToRefresh} {...downloadProps} />) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}

            <h3>Machine Translation</h3>
            {mt ? (<ModelCart modelDetails={mt} setRequestFile={setRequestFile} setNeedToRefresh={setNeedToRefresh} {...downloadProps} />) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}

            <h3>Text to Speech</h3>
            {tts ? (<ModelCart modelDetails={tts} setRequestFile={setRequestFile} setNeedToRefresh={setNeedToRefresh} {...downloadProps} />) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}
        </>
    )
}

function DownloadingBar() {
    return (
        <>Downloading....</>
    )
}

function FileRemovingWarrningPOPUP({ requestFile, onConfirm, onCancel }) {

    return (
        <div>
            <p>Are you sure you want to remove "{requestFile}" ?</p>
            <button onClick={onConfirm}>Yes</button>
            <button onClick={onCancel}>Cancle</button>
        </div>
    )
}