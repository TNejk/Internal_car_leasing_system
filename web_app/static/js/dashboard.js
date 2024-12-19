function fetchCarData(carId, token){
  fetch('https://icls.sosit-wh.net/get_full_car_info', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ 'car_id': carId })
    })
    .then(response => response.json())
    .then(data => {
      renderDetails(data['car_details']);
      calendar = renderCalendar(data['notallowed_dates']);

      document.getElementById('default-message').setAttribute('style', 'display:none');
      document.getElementById('car-details').setAttribute('style', 'display:flex');
      calendar.render();
    }).catch(error => console.error('Error fetching car details:', error));
};

function renderCalendar(dates) {
  const calendarEl = document.getElementById('calendar');

  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'timeGridWeek',
    locale: 'sk',
    selectable: true,
    selectOverlap: true,
    unselectAuto: false,
    eventOverlap: false,
    nowIndicator: true,
    selectMirror: true,
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'timeGridWeek,timeGridDay'
    },
    footerToolbar: {
      center: 'lease'
    },
    customButtons: {
      lease: {
        text: 'Lease Car',
        dateClick: function (info) {
          console.log(info.start);
          console.log(info.end);
        }
      }
    },


    events: [
      // { title: 'Event 1', start: '2024-11-10' }, // Sample event
      // { title: 'Event 2', start: '2024-11-12', end: '2024-11-14' }, // Multi-day event
      // { title: 'Event 3', start: '2024-11-15T10:30:00', allDay: false } // Timed event
    ],
    select: function(addInfo){}
  });

  return calendar;
};

function renderDetails(car_details) {
  const carDetails = car_details[0];
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
      document.getElementById("car-name").textContent = `Auto - ${carDetails[1]}`;
      document.getElementById("car-type").textContent = `Typ - ${carDetails[2]}`;
      document.getElementById("car-status").textContent = `Stav - ${carDetails[3]}`;
      document.getElementById("car-health").textContent = `Zdravie - ${carDetails[4]}`;
      document.getElementById("car-frequency").textContent = `Frekvencia obsadenia - ${carDetails[5]}`;
      document.getElementById("car-location").textContent = `Domáce mesto - ${carDetails[6]}`;

      // Check if an image URL exists
      if (carDetails[7]) {
        document.getElementById("car-image").src = carDetails[7];
        document.getElementById("car-image").alt = `Auto ${carDetails[1]}`;
      } else {
        // Use default image if none is provided
        document.getElementById("car-image").src = "https://pictures.dealer.com/m/maguirechevrolet/0087/a976281f56ff06d46dc390283aa14da6x.jpg?impolicy=downsize_bkpt&imdensity=1&w=520";
        document.getElementById("car-image").alt = "Auto";
      }
};

document.addEventListener('DOMContentLoaded', function() {});
