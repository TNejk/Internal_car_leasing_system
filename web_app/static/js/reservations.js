const closeModal = document.getElementById('close-modal');
const modalLeaseDetails = document.getElementById('modal-lease-details');
const modalStatus = document.getElementById('modal-status');
const closeModalStatus = document.getElementById('close-modal-status');
const modalBackdrop = document.getElementById('modal-backdrop');
const modalInner = document.getElementById('modal-inner');
const modalReturnCar = document.getElementById('modal-return-car');

const finishReservationButton = document.getElementById('finish-reservation-button');
const scrapReservationButton = document.getElementById('scrap-reservation-button');
const returnCarButton = document.getElementById('return-car-button');
const stopReturnButton = document.getElementById('stop-return-button');

const userList = document.getElementById('user-list');

let leaseId;
let role;

function get_leases(){
  fetch('/get_session_data', {method: 'POST'})
  .then(res => res.json())
  .then(data => {
    role = data.role;

    fetch('/get_user_leases', {method: 'POST'})
    .then(res => res.json())
    .then(data => {
      // Loop through `data` first, then check if each email exists in `userList`
      for (let lease of data) {
        let exists = false;

        // Check if the option already exists in the select list
        for (let option of userList.options) {
          if (option.value === lease.email) {
            exists = true;
            break; // Stop checking if found
          }
        }

        // Add only if the email is not in the select list
        if (!exists) {
          const user = new Option(lease.email, lease.email);
          userList.add(user);
        }
      }

      if (data.length <= 0) {
        document.getElementById('default-message').style.display = 'block';
      }else {
        if (role === 'manager'){
          if (userList.value === 'users'){
            render_cards(data);
          } else {
            const filteredData = data.filter(lease => lease.email === userList.value);
            render_cards(filteredData);
          }
        } else {
          render_cards(data);
        }
      }
    });
  })
} // finished

function render_cards(data){
        // Get the container where cards will be added
        const cardCont = document.getElementById('card-container');
        cardCont.innerHTML = ''; // Clear existing cards
        // Loop through each reservation in data
        for (let lease of data) {
          const formatter = new Intl.DateTimeFormat("sk-SK", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

        // Assuming lease['time_from'] and lease['time_to'] are in the format "YYYY-MM-DD HH:MM:SS"
        let from = lease['time_from'].replace(' ', 'T'); // Fix format
        let to = lease['time_to'].replace(' ', 'T'); // Fix format

        // Convert to Date objects
        from = new Date(from);
        to = new Date(to);

        // Format properly
        from = formatter.format(from);
        to = formatter.format(to);

          // Create a new card element dynamically
          const card = document.createElement('div');
          card.classList.add('card');
          card.onclick = function () {
              openModal(lease);
          };
          card.id = 'card';

          // Create car image
          const img = document.createElement('img');
          img.src = lease.url;
          img.alt = lease.car_name;
          card.appendChild(img);

          // Create car name element
          const carName = document.createElement('h2');
          carName.innerText = lease.car_name;
          card.appendChild(carName);

          const spz = document.createElement('h3');
          spz.innerText = lease.spz;
          card.appendChild(spz);

          // Create reservation time elements
          const timeFrom = document.createElement('p');
          timeFrom.innerText = `Od: ${from}`;
          card.appendChild(timeFrom);

          const timeTo = document.createElement('p');
          timeTo.innerText = `Do: ${to}`;
          card.appendChild(timeTo);

          // Add user info if role is manager
          if (role === 'manager') {
            const userInfo = document.createElement('p');
            userInfo.innerText = `Objednal: ${lease.email}`;
            card.appendChild(userInfo);
          }
          // Add card to the container
          cardCont.appendChild(card);
        }
} // finished

function finishReservation(){
  function formatDate() {
    const date = new Date();
    return date.toISOString().replace('T', ' ').replace('Z', '') + "+0000";
  }

  const note = document.getElementById("note").value;
  const health = document.getElementById("card-health").value;
  const location = document.getElementById("card-location").value;

  fetch('/get_session_data', {method: 'POST'})
    .then(response => response.json())
    .then(data => {
      let token = data.token;
      const returnTime = formatDate();
      const payload = {
        'id_lease': leaseId,
        'time_of_return': returnTime,
        'note': note,
        'location': location,
        'health': health
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
          closeModalF();
          modalReturnCar.style.display = 'none';
          reload(data);
          get_leases();
        }).catch((error) => console.error('Error fetching car details:', error));
    });} // finished

function scrapReservation(){
  let car = stopReturnButton.value;
  fetch('/get_session_data', {method: 'POST'})
    .then(response => response.json())
    .then(data => {
      let token = data.token;
      let email = data.username;

      fetch('https://icls.sosit-wh.net/cancel_lease', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + token,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({"car_name": car, "recipient": email}),
        }).then(response => response.json())
          .then((data) => {
            closeModalF();
            reload(data);
            get_leases();
        })
    });
}

function openModal(lease) {
  leaseId = lease.lease_id;

  const formatter = new Intl.DateTimeFormat("sk-SK", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  // Assuming lease['time_from'] and lease['time_to'] are in the format "YYYY-MM-DD HH:MM:SS"
  let from = lease['time_from'].replace(' ', 'T'); // Fix format
  let to = lease['time_to'].replace(' ', 'T'); // Fix format

  // Convert to Date objects
  from = new Date(from);
  to = new Date(to);

  // Format properly
  from = formatter.format(from);
  to = formatter.format(to);


  document.getElementById("modal-car-name").innerText = `${lease['car_name']}`;
  document.getElementById("modal-time-from").innerText = `Rezervované od:\n${from}`;
  document.getElementById("modal-time-to").innerText = `Rezervovaná do:\n${to}`;
  document.getElementById("modal-spz").innerText = `SPZ auta:\n${lease['spz']}`;
  stopReturnButton.value = lease['car_name'];
  if (role === 'manager') {
    document.getElementById("modal-user").innerText = `Objednal:\n${lease['email']}`;
  }
  modalLeaseDetails.style.display = "block";
  modalBackdrop.style.display = "block";
} // finished

function closeModalF(){
  modalLeaseDetails.style.display = "none";
  modalReturnCar.style.display = "none";
  modalBackdrop.style.display = "none";
} // finished

closeModal.addEventListener('click', function(){
  modalLeaseDetails.style.display = "none";
  modalReturnCar.style.display = "none";
  modalBackdrop.style.display = "none";
}); // finished

finishReservationButton.addEventListener('click', () => {
  modalLeaseDetails.style.display = "none";
  modalReturnCar.style.display = "block";
}); // finished

scrapReservationButton.addEventListener('click', () => {
  scrapReservation()
}); // finished

returnCarButton.addEventListener('click', () => {
  finishReservation();
}) // finished

stopReturnButton.addEventListener('click', () => {
  closeModalF();
}) // finished

function reload(data){
  let set = false;
  const status = data['status'];
  const canceled = data['cancelled'];
  const modalTitle = document.querySelector('#modal-status #modal-inner h2');
  const modalMessage = document.querySelector('#modal-status #modal-inner p');
  console.log(set);
  if (status === 'returned' && set === false){
    modalTitle.textContent = 'Úspech :)';
    modalMessage.textContent = 'Auto bolo úspešne vtárené!';
    set = true;
  }
  else if (canceled === true && set === false){
    modalTitle.textContent = 'Úspech :)';
    modalMessage.textContent = 'Rezervácia bola zrušená!';
    set = true;
  }

  if (!status && set === false) {
    modalTitle.textContent = 'Neúspech :(';
    modalMessage.textContent = 'Auto sa nepodarilo vrátiť! Obnovte stránku a skúste to znova.';
    set = true;
  }else if (!canceled&& set === false){
    modalTitle.textContent = 'Neúspech :(';
    modalMessage.textContent = 'Rezerváciu sa nepodarilo zrušiť! Obnovte stránku a skúste to znova.';
    set = true;
  }
  modalStatus.style.display = 'block';
  modalInner.style.display = 'block';
  modalBackdrop.style.display = 'block';
} // finished

closeModalStatus.addEventListener('click', function() {
  modalBackdrop.style.display = "none";
  modalStatus.style.display = "none";
}) // finished

try{
  userList.addEventListener('click', function () {
  get_leases()
  })
}
catch {
  console.log();
} // finished

document.addEventListener('DOMContentLoaded', () => {
  get_leases();
  modalInner.style.display = 'none';
}) // finished