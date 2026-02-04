const cardContainer =  document.getElementById('cards-container');

function get_requests(){

  fetch('/manager/get_requests', {method: 'GET'})
    .then(response => response.json()).then(data => {
      cardContainer.innerHTML = '';
      requests = data['active_requests'];
      if (requests.length > 0) {
        document.getElementById('default-message').style.display = 'none';
        //car_name: "Škoda Scala", email: "test@user.sk", location: "BB", request_id: 43, role: "user", spz: "BB400GT", time_from: "2025-06-19 12:30:00", time_to: "2025-06-20 19:00:00", url: "https://fl.gamo.sosit-wh.net/skoda-scala.webp"
        for (const r of requests) {
          const card = document.createElement('div');
          card.classList.add("card");

          const img = document.createElement("img");
          img.classList.add("card-image");
          img.src = r.url;
          card.appendChild(img);

          const content = document.createElement("div");
          content.classList.add("card-content");

          const title = document.createElement("p");
          title.classList.add("card-title");
          title.innerHTML = `${r.car_name}<br>${r.email}`;
          content.appendChild(title);

          const message = document.createElement("p");
          message.classList.add("card-message");
          message.innerHTML = `ŠPZ: ${r.spz}<br>Oblasť: ${r.location}<br>Od: ${r.time_from}<br>Do: ${r.time_to}`;
          content.appendChild(message);

          const buttons = document.createElement('div');
          buttons.classList.add("card-buttons");

          const approveButton = document.createElement("button");
          approveButton.classList.add("card-button", "approve");
          approveButton.textContent = 'Povoliť';
          approveButton.onclick = function () {
            approve(r.request_id, r.time_from, r.time_to, r.car_name, r.email);
          };
          buttons.appendChild(approveButton);

          const denyButton = document.createElement("button");
          denyButton.classList.add("card-button", "deny");
          denyButton.textContent = 'Zamietnuť';
          denyButton.onclick = function () {
            deny(r.request_id, r.time_from, r.time_to, r.car_name, r.email);
          };
          buttons.appendChild(denyButton);

          content.appendChild(buttons);
          card.appendChild(content);
          cardContainer.appendChild(card);
        }

      }else {
        document.getElementById('default-message').style.display = 'block';
      }
  })
}

function approve(r_id,t_fr, t_to, c_id, r){

  let data = {
    'approval': true,
    'request_id': r_id,
    'timeof': t_fr,
    'timeto': t_to,
    'id_car': c_id,
    'reciever': r
  }

  fetch('/manager/approve_requests', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
    .then(res => res.json()).then(data => {
      if (data.status === true){
        get_requests()
      }
    })
}

function deny(r_id,t_fr, t_to, c_id, r){
   let data = {
    'approval': false,
    'request_id': r_id,
    'timeof': t_fr,
    'timeto': t_to,
    'id_car': c_id,
    'reciever': r
  }

  fetch('/manager/approve_requests', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
    .then(res => res.json()).then(data => {
      if (data.status === true){
        get_requests()
      }
    })
}

document.addEventListener("DOMContentLoaded", () => {
  get_requests()
})