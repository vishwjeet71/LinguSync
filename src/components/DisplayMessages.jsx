import { useEffect, useState } from "react";

export default function useDisplayMessage(displayTime = 5000) {
    const [messageQueue, setMessageQueue] = useState([]);
    const [currentMessage, setCurrentMessage] = useState("");

    const setDisplayMessage = (message) => {
        if (!message) return;

        setMessageQueue((prevQueue) => [
            ...prevQueue,
            message
        ]);
    };

    useEffect(() => {
        // Don't start another message while one is already displayed
        if (currentMessage || messageQueue.length === 0) {
            return;
        }

        const [nextMessage, ...remainingMessages] = messageQueue;

        setCurrentMessage(nextMessage);
        setMessageQueue(remainingMessages);
    }, [messageQueue, currentMessage]);

    useEffect(() => {
        if (!currentMessage) {
            return;
        }

        const timeoutId = setTimeout(() => {
            setCurrentMessage("");
        }, displayTime);

        return () => {
            clearTimeout(timeoutId);
        };
    }, [currentMessage, displayTime]);

    return {
        currentMessage,
        setDisplayMessage,
    };
}