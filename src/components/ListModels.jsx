export default function ListModels({ modelsManifest }) {

    const em = modelsManifest.efficient;
    const pm = modelsManifest.performance;

    return (
        <>
            <div>
                <div>
                    {em && Object.keys(em).length > 0 ? (<><h2>Efficient Models</h2>
                        <ModelBlock blockDetail={em} /></>) : null}
                </div>
                <div>
                    {pm && Object.keys(pm).length > 0 ? (<><h2>Performance Models</h2>
                        {JSON.stringify(pm)}</>) : null}
                </div>
            </div>
        </>
    )
}

function ModelBlock({ blockDetail }) {

    const stt = blockDetail?.stt;
    const mt = blockDetail?.mt;
    const tts = blockDetail?.tts;

    return (
        <>
            <h3>Speech To Text model</h3>
            {stt ? (<>{JSON.stringify(stt)}</>) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}

            <h3>Machine Translation</h3>
            {mt ? (<>{JSON.stringify(mt)}</>) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}

            <h3>Text to Speech</h3>
            {tts ? (<>{JSON.stringify(tts)}</>) : (<p>Looks like support for this model hasn't been implemented yet.</p>)}
        </>
    )
}