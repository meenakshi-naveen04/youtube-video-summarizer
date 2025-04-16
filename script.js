document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("summarizeBtn").addEventListener("click", async () => {
        const videoUrl = document.getElementById("videoUrl").value;
        if (!videoUrl) {
            alert("Please enter a YouTube URL!");
            return;
        }

        document.getElementById("summary").innerText = "Summarizing... ⏳";

        const response = await fetch("/summarize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ youtube_url: videoUrl, max_length: 120, min_length: 50 }),
        });

        const result = await response.json();
        document.getElementById("summary").innerText = result.summary || "Error: " + result.error;
    });
});
