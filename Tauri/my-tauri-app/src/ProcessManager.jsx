import React, { useState } from 'react';
import { Command } from '@tauri-apps/plugin-shell';

export default function ProcessManager() {
  const [status, setStatus] = useState('Not Running');
  const [pid, setPid] = useState('—');
  const [childProcess, setChildProcess] = useState(null);

  const handleStart = async () => {
    try {
      // Command create karo
      const command = Command.create('sleep', ['30']);

      // Event Listeners
      command.on('close', data => {
        console.log(`Process closed with code: ${data.code}`);
        setStatus('Stopped');
        setPid('—');
      });
      command.on('error', error => console.error(`Process error: ${error}`));
      command.stdout.on('data', line => console.log(`stdout: ${line}`));
      command.stderr.on('data', line => console.log(`stderr: ${line}`));


      const child = await command.spawn();
      setChildProcess(child);
      setPid(child.pid);
      setStatus('Running');
    } catch (err) {
      console.error('Failed to spawn process:', err);
    }
  };

  const handleStop = async () => {
    if (childProcess) {
      await childProcess.kill();
      setChildProcess(null);
      setStatus('Stopped');
      setPid('—');
    }
  };

  return (
    <div style={{ border: '1px solid #ccc', padding: '20px', width: '280px', borderRadius: '8px' }}>
      <h2>Process Manager</h2>
      <p>Status: <strong>{status}</strong></p>
      <p>PID: <strong>{pid}</strong></p>
      <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
        <button onClick={handleStart} disabled={status === 'Running'}>
          Start
        </button>
        <button onClick={handleStop} disabled={status !== 'Running'}>
          Stop
        </button>
      </div>
    </div>
  );
}