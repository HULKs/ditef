import { useState, useEffect, useRef } from "react";

export default function useWebSocket(enable, url, callback) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState();
  const websocket = useRef(null);

  useEffect(() => {
    if (enable) {
      websocket.current = new WebSocket(url);

      websocket.current.onopen = () => {
        setConnected(true);
        setError();
      };

      websocket.current.onclose = () => {
        if (websocket.current) {
          setConnected(false);
        }
      };

      websocket.current.onerror = error => {
        setError(error);
      };

      websocket.current.onmessage = event => {
        const message = JSON.parse(event.data);

        for (const [type, payload] of Object.entries(message)) {
          callback(type, payload);
        }
      };

      return () => {
        websocket.current.close();
        websocket.current = null;
      };
    } else {
      setConnected(false);
    }
  }, [enable, url]);

  return [
    connected,
    error,
    (type, payload) => {
      websocket.current.send(JSON.stringify({
        ...payload,
        type: type,
      }));
    },
  ];
}
