document.addEventListener("DOMContentLoaded", () => {
    const dateInput = document.querySelector('input[name="transaction_date"]');
    if (dateInput && !dateInput.value) {
        const today = new Date();
        const offset = today.getTimezoneOffset();
        const localDate = new Date(today.getTime() - offset * 60000)
            .toISOString()
            .split("T")[0];
        dateInput.value = localDate;
    }

    document.querySelectorAll(".flash").forEach((flash) => {
        setTimeout(() => {
            flash.classList.add("fade-out");
        }, 4500);
    });
});
