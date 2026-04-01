async function getState() {
    let res = await fetch("/state");
    let data = await res.json();

    let item = document.getElementById("item");

    let color = data.items[0].color;
    item.style.background = color;

    let position = data.items[0].position;
    item.style.left = (position * 70) + "px";

    document.getElementById("score").innerText = "Score: " + data.score;

    // Auto reset when done
    if (data.done) {
        setTimeout(() => {
            fetch("/reset");
        }, 1000);
    }
}

async function sendAction(action) {
    let res = await fetch("/step?action=" + action, { method: "POST" });
    let data = await res.json();

    let item = document.getElementById("item");

    if (data.score > 0) {
        item.classList.add("correct");
    } else {
        item.classList.add("wrong");
    }

    setTimeout(() => {
        item.classList.remove("correct", "wrong");
    }, 500);

    getState();
}

setInterval(getState, 700);