const startRecording = async () => {
  if (!meetingId || isRecording) return;

  try {
    setStatus("Requesting microphone...");

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });

    streamRef.current = stream;

    const ws = new WebSocket(
      `${WS_BASE}/transcription/ws/${meetingId}?speaker_name=${encodeURIComponent(userName)}`
    );

    ws.onopen = () => {
      console.log("WebSocket Connected");
      setStatus("Recording started... speak now!");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Transcript:", data);

        if (data.text) {
          setTranscript((prev) => [
            ...prev,
            `[${data.speaker}]: ${data.text}`,
          ]);
        }
      } catch (e) {
        console.error(e);
      }
    };

    ws.onerror = (err) => {
      console.error("WS Error:", err);
      setStatus("Transcription connection error!");
    };

    websocketRef.current = ws;

    let mimeType = "";

    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
      mimeType = "audio/webm;codecs=opus";
    } else if (MediaRecorder.isTypeSupported("audio/webm")) {
      mimeType = "audio/webm";
    }

    const mediaRecorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream);

    mediaRecorder.ondataavailable = async (event) => {
      console.log("Chunk Size:", event.data.size);

      if (event.data.size === 0) return;

      if (
        websocketRef.current &&
        websocketRef.current.readyState === WebSocket.OPEN
      ) {
        const buffer = await event.data.arrayBuffer();
        websocketRef.current.send(buffer);
        console.log("Audio chunk sent");
      }
    };

    // ✅ IMPORTANT
    mediaRecorder.start(2000);

    mediaRecorderRef.current = mediaRecorder;

    setIsRecording(true);
    setStatus("Recording... speak now!");
  } catch (err) {
    console.error(err);
    alert("Please allow microphone access.");
    setStatus("");
  }
};