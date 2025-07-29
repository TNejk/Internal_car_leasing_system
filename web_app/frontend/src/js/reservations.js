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

const filter = document.getElementById('filter');
const userList = document.getElementById('user-list');
const carList = document.getElementById('car-list');
const statusTrue = document.getElementById('status-true');
const statusFalse = document.getElementById('status-false');
const timeof = document.getElementById('timeof');
const timeto = document.getElementById('timeto');

const carDamaged = document.getElementById('car-damaged');
const carDamagedParams = document.getElementById('car-damaged-params');
const carCollision = document.getElementById('car-collision');

let leaseId;
let role;

function get_leases() {
  fetch('/get_session_data', {method: 'POST'})
  .then(res => res.json())
  .then(data => {
    role = data.role;
    username = data.username;
    let payload;
    if (role === 'manager'){
      payload = JSON.stringify({car_name: carList.value, email: userList.value, timeof: timeof.value, timeto: timeto.value, istrue: statusTrue.checked, isfalse: statusFalse.checked})
    }else {
      payload = JSON.stringify({car_name: '', email: username, timeof: timeof.value, timeto: timeto.value, istrue: statusTrue.checked, isfalse: statusFalse.checked})
    }

    fetch('/get_user_leases', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: payload,})
    .then(res => res.json())
    .then(data => {
      if (!data){
        document.getElementById('default-message').style.display = 'block';
      }else {
        if (role === 'manager'){
          if (userList.value === ''){
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
  for(let lease of data) {
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
    if (lease.status === false){
      card.style.backgroundColor = '#bc2026';
    }else if(lease.status === true){
      // !!!!!!!!!!!!!!!! kamo skontroluj si vzdy ked porovnavas casy, ci su rovnako sformatovane, ci su rovnaka timezone lebo toISOString vzdy da cas o 2 hodiny dozadu idk why >:)
      const now = new Date();
      now.setHours(now.getHours() + 2);
      let date = now.toISOString().replace('T', ' ').split('.')[0];
      if (date < lease.time_from){
        card.style.backgroundColor = 'orange';
      }else {
        card.style.backgroundColor = 'green';
      }
    }

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
    return date.toISOString().replace('T', ' ').replace('Z', '').split('.')[0];
  }

  const location = document.getElementById("car-location").value;
  let damaged = document.getElementById("car-damaged").checked;
  let dirty = document.getElementById("car-dirty").checked;
  let intDmg = document.getElementById("car-int-dmg").checked;
  let extDmg = document.getElementById("car-ext-dmg").checked;
  let collision = document.getElementById("car-collision").checked;

  const note = document.getElementById("note").value;

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
        'damaged': damaged,
        'dirty': dirty,
        'int_damage': intDmg,
        'ext_damage': extDmg,
        'collision': collision
      };
      console.log(JSON.stringify(payload))
      fetch('/return_car', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + token,
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
      let email;
      if (data.role === 'user'){
        email = data.username;
      }else {
        email = document.getElementById('modal-user').innerHTML.split('>')[1];
      }

      fetch('/cancel_lease', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({"car_name": car, "recipient": email}),
        }).then(response => response.json())
          .then((data) => {
            closeModalF();
            reload(data);
            get_leases();
        });
    });
}

function openModal(lease) {
  leaseId = lease.lease_id;
  if (lease.status === false) {
      document.getElementById('finish-reservation-button').style.display = 'none';
      document.getElementById('scrap-reservation-button').style.display = 'none';
    }else {
      document.getElementById('finish-reservation-button').style.display = 'block';
      document.getElementById('scrap-reservation-button').style.display = 'block';}

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
  document.getElementById("modal-state").innerText = `Status:\n${lease['status'] === true ? 'Aktívny' : 'Ukončený'}`;
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
  const checkboxes = document.querySelectorAll('#car-damaged-params input[type="checkbox"]');
  // Disable each one
  checkboxes.forEach(cb => cb.checked = false);
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
  const checkboxes = document.querySelectorAll('#car-damaged-params input[type="checkbox"]');
  carDamaged.checked = false;
  carDamagedParams.style.display = "none";
  checkboxes.forEach(cb => cb.checked = false);
  closeModalF();
}) // finished

carDamaged.addEventListener('click', () => {
  let state = carDamaged.checked;
  if (state === true) {
    carDamagedParams.style.display = 'block';
  }else {
    carDamagedParams.style.display = 'none';
    const checkboxes = document.querySelectorAll('#car-damaged-params input[type="checkbox"]');
    // Disable each one
    checkboxes.forEach(checkbox => {
      checkbox.checked = false;
    });
  }

})

carCollision.addEventListener('click',() =>{
  let state = carCollision.checked;
  if (state === true) {
    const checkboxes = document.querySelectorAll('#car-damaged-params input[type="checkbox"]');
    // Disable each one
    checkboxes.forEach(checkbox => {
      checkbox.checked = true;
    });
  }else{
    const checkboxes = document.querySelectorAll('#car-damaged-params input[type="checkbox"]');
    // Disable each one
    checkboxes.forEach(checkbox => {
      checkbox.checked = false;
    });}
})

function reload(data){
  let set = false;
  const status = data['status'];
  const canceled = data['cancelled'];
  const modalTitle = document.querySelector('#modal-status #modal-inner h2');
  const modalMessage = document.querySelector('#modal-status #modal-inner p');
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
  }else if (!canceled&& set === false){
    modalTitle.textContent = 'Neúspech :(';
    modalMessage.textContent = 'Rezerváciu sa nepodarilo zrušiť! Obnovte stránku a skúste to znova.';
  }
  modalStatus.style.display = 'block';
  modalInner.style.display = 'block';
  modalBackdrop.style.display = 'block';
} // finished

if (filter !== null) {
  filter.addEventListener('click', function () {
    get_leases();
  })
}
closeModalStatus.addEventListener('click', function() {
  modalBackdrop.style.display = "none";
  modalStatus.style.display = "none";
}) // finished

document.addEventListener('DOMContentLoaded', () => {
  get_leases();
  modalInner.style.display = 'none';

  if (role === 'manager') {
    fetch('get_cars', {method: 'POST'}).then(res => res.json()).then(data => {
      for (let car of data) {
        const opt = new Option(car[0],car[0]);
        carList.add(opt);
      }
    })
    fetch('get_users', {method: 'POST'}).then(res=> res.json()).then(data => {
      for (let user of data) {
        const opt = new Option(user.email,user.email);
        userList.add(opt);
      }
    })
  }
}) // finished