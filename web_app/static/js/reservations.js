const closeModal = document.getElementById('close-modal');
const finishReservationModal = document.getElementById('finish-reservation-modal');
const scrapReservationModal = document.getElementById('scrap-reservation-modal');
const modal = document.getElementById('modal');
let leaseId;
let token;

function get_leases{
  fetch('/get_session_data', {method: 'POST'})
    .then(res => res.json())
    .then(data => {
      var username = data.username;
      var token = data.token;
      var role = data.role;
      var data = {'email': username, 'role': role};

      fetch('https://icls.sosit-wh.net/get_leases', {
        method: 'POST',
        headers: {
                Authorization: 'Bearer ' + Token,
                'Content-Type': 'application/json'},
              body: JSON.stringify(data)
      })
        .then(res => res.json())
        .then(data => {
          if (!data){
            document.getElementById('default-message').style.display = 'block';
          }
          else {
            for (lease in data) {
              document.getElementById('reservation-card').onclick = openModal(lease.lease_id);
              document.getElementById('reservation-car-image').src = lease.url;
              document.getElementById('reservation-car-image').alt = lease.car_name;
              document.getElementById('reservation-car-name').innerText = lease.car_name;
              document.getElementById('reservation-time_from').innerText = lease.time_from;
              document.getElementById('reservation-time-to').innerText = lease.time_to;
              if (role == 'manager'){
                document.getElementById('reservation-user').innerText = lease.email;
              }

              document.getElementById('reservations-card').style.display = 'block';
            }
          }
        });
    });
};

function openModal(lease) {
  leaseId = lease.lease_id;
  document.getElementById("modal-car-name").innerText = lease['car_name'];
  document.getElementById("modal-time-from").innerText = lease['time_from'];
  document.getElementById("modal-time-to").innerText = lease['time_to'];
  document.getElementById("modal-user").innerText = lease['email'];
  document.getElementById("modal").style.display = "block";
  document.getElementById("modal-backdrop").style.display = "block";
};

closeModal.addEventListener('click', () => {
  document.getElementById("modal").style.display = "none";
  document.getElementById("modal-backdrop").style.display = "none";
});

finishReservationModal.addEventListener('click', () => {
  function formatDate(date) {
    const year = date.substr(0, 4);
    const month = date.substr(5, 2);
    const day = date.substr(8, 2);
    const hours = date.substr(11, 2);
    const minutes = date.substr(14, 2);
    const seconds = date.substr(17, 2);
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  fetch('/get_session_data', {method: 'POST'})
    .then(response => response.json())
    .then(data => {
      token = data.token;
      console.log(token);

      const returnTime = formatDate(new Date().toISOString());
      const payload = {
        "id_lease": leaseId,
        "time_of_return": returnTime,
        "note": '',
        'location': 'Banská Bystrica',
        'health': 'good'
      };
      fetch('https://icls.sosit-wh.net/return_car', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + token,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }).then((response) => response.json())
        .then((data) => {
          console.log(data);
        }).catch((error) => console.error('Error fetching car details:', error));
    });

});

scrapReservationModal.addEventListener('click', () => {
  console.log("Scrap Reservation");
});

document.addEventListener('DOMContentLoaded', () => {

})