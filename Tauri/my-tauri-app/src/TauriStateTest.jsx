import React, { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

export default function TauriStateTest() {
  const [counter, setCounter] = useState(0);

  const handleIncrease = async () => {
    try {
      const val = await invoke('increase_counter');
      setCounter(val);
    } catch (err) {
      console.error('Error increasing counter:', err);
    }
  };

  const handleGetCounter = async () => {
    try {
      const val = await invoke('get_counter');
      setCounter(val);
    } catch (err) {
      console.error('Error getting counter:', err);
    }
  };

  return (
    <div style={{ border: '1px solid #ccc', padding: '20px', width: '280px', borderRadius: '8px' }}>
      <h2>Tauri State Test</h2>
      <p>Counter: <strong>{counter}</strong></p>
      <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
        <button onClick={handleIncrease}>Increase</button>
        <button onClick={handleGetCounter}>Get Counter</button>
      </div>
    </div>
  );
}