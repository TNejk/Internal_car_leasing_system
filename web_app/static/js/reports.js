const cardContainer = document.getElementById('card-container');

function get_reports() {
  fetch('/manager/get_all_reports', {method: 'GET'}).then(res => res.json()).then((data) => {
    // [[report,report]]
    console.log(data);
    const reports = data[0]; // [report,report]
    console.log(reports);

    if (reports.length < 0) {
      document.getElementById('loading-message').style.display = 'none';
      const def_message = document.createElement("div");
      def_message.setAttribute("id", "default-message");
      def_message.innerHTML = 'Neexistujú žiadne mesačné reporty!';
      cardContainer.appendChild(def_message);
    }else {
      document.getElementById('loading-message').style.display = 'none';
      reports.forEach(report => {
        const card = document.createElement('div');
        card.classList.add('card');
        card.onclick = function () {
          download_report(report);
        };
        card.id = 'card';

        const name = document.createElement('h2');
        name.innerHTML = report;
        card.appendChild(name);

        const img = document.createElement('img');
        img.src = '../static/sources/images/download.svg';
        card.appendChild(img);

        cardContainer.appendChild(card);

      })
    }
  })
}

function download_report(report) {
  window.open('/manager/get_report?report='+report, {method: 'GET'})
}

document.addEventListener("DOMContentLoaded", () => {
  get_reports()
})