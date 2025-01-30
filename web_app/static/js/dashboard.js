let selectedRange = null;
let username = null;
let recipient = null;
let role = null;
let car_name = null;
let is_private = false;
let Token = null;
let car_id = null;
let stk = null;

const closeModal = document.getElementById('close-modal');
const modal = document.getElementById('modal');

function fetchCarData(carId, token, user, useRole) {
  fetch('https://icls.sosit-wh.net/get_full_car_info', {
    method: 'POST',
    headers: {
      Authorization: 'Bearer ' + token,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ car_id: carId }),
  })
    .then((response) => response.json())
    .then((data) => {
      renderDetails(data['car_details']);
      const calendar = renderCalendar(data['notallowed_dates']);
      document.getElementById('default-message').style.display = 'none';
      document.getElementById('car-details').style.display = 'flex';
      calendar.render();
    })
    .catch((error) => console.error('Error fetching car details:', error));
  username = user;
  role = useRole;
  Token = token;
  car_id = carId;
}

function renderCalendar(dates) {
  const calendarEl = document.getElementById('calendar');
  const today = new Date(); // Get today's date

  const calendar = new FullCalendar.Calendar(calendarEl, {
    height: 650,
    initialView: 'timeGridWeek',
    locale: 'sk',
    selectable: true,
    selectOverlap: false,
    unselectAuto: true,
    eventOverlap: false,
    nowIndicator: true,
    selectMirror: true,

    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'timeGridWeek,timeGridDay',
    },

    footerToolbar: {
      center: 'lease',
    },

    customButtons: {
      lease: {
        text: 'Rezervuj!',
        click: function () {
          if (selectedRange) {
            data = {
              'username': username,
              'recipient': username, // zmen na recipient ked budes robit managera
              'role': role,
              'car_name': car_name,
              'stk': stk,
              'is_private': is_private,
              'timeof': selectedRange['start'],
              'timeto': selectedRange['end'],
            };
            fetch('https://icls.sosit-wh.net/lease_car', {
              method: 'POST',
              headers: {
                Authorization: 'Bearer ' + Token,
                'Content-Type': 'application/json'},
              body: JSON.stringify(data)
            })
              .then(response => response.json())
              .then(data => {
                reload(data);
                fetchCarData(car_id, Token, username, role);
              })
              .catch(error => console.error('Error:', error));
          } else {
            console.log('No range selected.');
          };
        },
      },
    },

    validRange: {
      start: today.toISOString().split('T')[0] // Disable dates before today
    },

    // selectAllow: function(selectInfo) {
    //   // Disallow times before the current time on the current day
    //   const today = new Date().toISOString().split('T')[0];
    //   const selectedStart = selectInfo.start;
    //   const selectedDate = selectedStart.toISOString().split('T')[0];
    //
    //   // If the selected date is today, ensure the time is in the future
    //   if (selectedDate === today) {
    //     const nowTime = now.getTime(); // Current time in milliseconds
    //     return selectedStart.getTime() >= nowTime; // Allow only if the start time is in the future
    //   }
    //
    //   return true; // Allow selection for future dates
    // },

    events: dates.map((event) => ({
      title: 'Obsadené',
      start: event[0],
      end: event[1],
    })),

    select: function (info) {
      function formatDate(date) {
        const year = date.substr(0,4);
        const month = date.substr(5,2);
        const day = date.substr(8,2);
        const hours = date.substr(11,2);
        const minutes = date.substr(14,2);
        const seconds = date.substr(17,2);
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
      }

      selectedRange = {
        start: formatDate(info.startStr),
        end: formatDate(info.endStr),
      };
    },
  });

  return calendar;
}

function renderDetails(car_details) {
  const carDetails = car_details[0];
  car_name = carDetails[1];
  stk = carDetails[8]
  if (carDetails[3] == 'stand_by') {
    carDetails[3] = 'Voľné';
  } else if (carDetails[3] == 'leased') {
    carDetails[3] = 'Obsadené';
  } else if (carDetails[3] == 'service') {
    carDetails[3] = 'V servise';
  } else {
    carDetails[3] = 'Kontaktujte administrátora :(';
  }
  // Map the car details correctly
  document.getElementById('car-name').textContent = `Auto - ${carDetails[1]}`;
  document.getElementById('car-type').textContent = `Typ - ${carDetails[2]}`;
  document.getElementById('car-status').textContent = `Stav - ${carDetails[3]}`;
  document.getElementById('car-health').textContent = `Zdravie - ${carDetails[4]}`;
  document.getElementById('car-frequency').textContent = `Frekvencia obsadenia - ${carDetails[5]}`;
  document.getElementById('car-location').textContent = `Domáce mesto - ${carDetails[6]}`;
  document.getElementById('car-spz').textContent = `SPZ - ${carDetails[8]}`;

  // Check if an image URL exists
  if (carDetails[7]) {
    document.getElementById('car-image').src = carDetails[7];
    document.getElementById('car-image').alt = `Auto ${carDetails[1]}`;
  } else {
    // Use default image if none is provided
    document.getElementById('car-image').src =
      'https://pictures.dealer.com/m/maguirechevrolet/0087/a976281f56ff06d46dc390283aa14da6x.jpg?impolicy=downsize_bkpt&imdensity=1&w=520';
    document.getElementById('car-image').alt = 'Auto';
  }
}

function reload(data){
  const status = data['status'];
  const modalTitle = document.querySelector('#modal .modal-inner h2');
  const modalMessage = document.querySelector('#modal .modal-inner p');
  if (status == true){
    modalTitle.textContent = 'Úspech :)';
    modalMessage.textContent = 'Rezervácia auta bola úspešná!';
  }else{
    modalTitle.textContent = 'Neúspech :(';
    modalMessage.textContent = 'Rezervácia auta sa nepodarila, skúste to znova.';
  }
  modal.classList.add('open');

};

closeModal.addEventListener('click', () => {
  modal.classList.remove('open')
});

