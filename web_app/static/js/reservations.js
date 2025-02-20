const closeModal = document.getElementById('close-modal');
const finishReservationModal = document.getElementById('finish-reservation-modal');
const scrapReservationModal = document.getElementById('scrap-reservation-modal');
const modal = document.getElementById('modal');
const modalStatus = document.getElementById('modal-status');
const closeModalStatus = document.getElementById('close-modal-status');
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
      console.log(data);
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


      if (!data){
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
}

function render_cards(data){
  // Get the container where cards will be added
        const cardCont = document.getElementById('card-container');
        cardCont.innerHTML = ''; // Clear existing cards
  // Loop through each reservation in data
        for (let lease of data) {

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

          // Create reservation time elements
          const timeFrom = document.createElement('p');
          timeFrom.innerText = `From: ${lease.time_from}`;
          card.appendChild(timeFrom);

          const timeTo = document.createElement('p');
          timeTo.innerText = `To: ${lease.time_to}`;
          card.appendChild(timeTo);

          // Add user info if role is manager
          if (role === 'manager') {
            const userInfo = document.createElement('p');
            userInfo.innerText = lease.email;
            card.appendChild(userInfo);
          }
          // Add card to the container
          cardCont.appendChild(card);
        }
}

function openModal(lease) {
  leaseId = lease.lease_id;
  console.log(lease);
  document.getElementById("modal-car-name").innerText = lease['car_name'];
  document.getElementById("modal-time-from").innerText = lease['time_from'];
  document.getElementById("modal-time-to").innerText = lease['time_to'];
  if (role === 'manager') {
    document.getElementById("modal-user").innerText = lease['email'];
  }
  document.getElementById("modal").style.display = "block";
  document.getElementById("modal-backdrop").style.display = "block";
};

function closeModalF(){
  document.getElementById("modal").style.display = "none";
  document.getElementById("modal-backdrop").style.display = "none";
};

closeModal.addEventListener('click', function(){
  document.getElementById("modal").style.display = "none";
});

finishReservationModal.addEventListener('click', () => {
  function formatDate() {
    const date = new Date();
    const formattedDate = date.toISOString().replace('T', ' ').replace('Z', '') + "+0000";
    return formattedDate;
  };

  const note = document.getElementById("note").value;
  const health = document.getElementById("card-health").value;
  const location = document.getElementById("card-location").value;

  fetch('/get_session_data', {method: 'POST'})
    .then(response => response.json())
    .then(data => {
      token = data.token;
      const returnTime = formatDate();
      const payload = {
        'id_lease': leaseId,
        'time_of_return': returnTime,
        'note': note,
        'location': location,
        'health': health
      };
      console.log(payload);
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
          reload(data);
          get_leases();
        }).catch((error) => console.error('Error fetching car details:', error));
    });
});

scrapReservationModal.addEventListener('click', () => {
  console.log("Scrap Reservation");
});

function reload(data){
  const status = data['status'];
  const modalTitle = document.querySelector('#modal-status #modal-inner h2');
  const modalMessage = document.querySelector('#modal-status #modal-inner p');
  if (status == 'returned'){
    modalTitle.textContent = 'Úspech :)';
    modalMessage.textContent = 'Rezervácia auta bola úspešná!';
  }else{
    modalTitle.textContent = 'Neúspech :(';
    modalMessage.textContent = 'Rezervácia auta sa nepodarila, skúste to znova.';
  }
  document.getElementById('modal-status').style.display = 'block';
  document.getElementById('modal-inner').style.display = 'block';
};

closeModalStatus.addEventListener('click', function() {
  document.getElementById("modal-backdrop").style.display = "none";
  document.getElementById('modal-status').style.display = "none";
})

try{
  userList.addEventListener('click', function () {
  get_leases()
  })
}catch {
  console.log();
}

document.addEventListener('DOMContentLoaded', () => {
  get_leases();
  document.getElementById('modal-inner').style.display = 'none';
})