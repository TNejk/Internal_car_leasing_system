import Calendar from '@toast-ui/calendar'

let selectedRange = null;
let username = null
let role = null;
let car_name = null;
let is_private = null;
let Token = null;
let car_id = null;
let stk = null;
let geojs = null;

function loadCarList(){
  fetch('/get_cars', {method: 'GET'})
    .then(response => response.json())
    .then(data => {
      // console.log(data['car_list']);
      //{
      //   "car_id": 1,
      //   "car_name": "Volkswagen Golf",
      //   "car_status": "available",
      //   "image_url": "https://fl.gamo.sosit-wh.net/wolks.jpg",
      //}
      let car_list_div = document.getElementById('car-list');

      for(let car of data['car_list']){
        let card = document.createElement('div');
        card.setAttribute('class', 'card');
        card.setAttribute('onclick', 'renderDetails(car.car_id)');

        let align = document.createElement('div');
        align.setAttribute('class', 'flex-inline');

        let img = document.createElement('img');
        img.setAttribute('src', car.image_url);
        align.appendChild(img);

        let name = document.createElement('h2');
        name.textContent = car.car_name;
        align.appendChild(name);

        let status = document.createElement('p');
        status.textContent = car.car_status;
        align.appendChild(status);

        card.appendChild(align);
        car_list_div.appendChild(card);
      }

    })
}

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
      renderCalendar(data['notallowed_dates']);
      document.getElementById('default-message').style.display = 'none';
      document.getElementById('car-details').style.display = 'flex';
      //calendar.render();
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

  const calendar = new Calendar(calendarEl, {
    defaultView: 'week',
    template: {
      time(event) {
        const { start, end, title } = event;

        return `<span style="color: white;">${start}~${end} ${title}</span>`;
      },

      allday(event) {
        return `<span style="color: gray;">${event.title}</span>`;
      },
    },

    calendars: [
      {
        id: 'cal1',
        name: 'Personal',
        backgroundColor: '#03bd9e',
      },
      {
        id: 'cal2',
        name: 'Work',
        backgroundColor: '#00a9ff',
      },
    ],

    // views: {
    //   timeGrid7Day: {
    //     type: 'timeGrid',
    //     duration: { days: 7 },
    //     buttonText: 'Týždeň'
    //   },
    //   timeGridDay: {
    //     buttonText: 'Deň'
    //   },
    //   timeGridToday: {
    //     buttonText: 'Dnes'
    //   }
    // },
    //
    // customButtons: {
    //   this: {
    //     buttonText: 'Dnes',
    //     click: function() {
    //       calendar.today();
    //     }
    //   },
    //   lease: {
    //     text: 'Rezervuj!',
    //     click: function () {
    //       if (selectedRange) {
    //         leaseCar(selectedRange);
    //       } else {
    //         console.log('No range selected.');
    //       };
    //     },
    //   },
    // },
    //
    // validRange: {
    //   start: today.toISOString().split('T')[0] // Disable dates before today
    // },
    //
    // events: dates.map((event) => ({
    //   title: 'Obsadené',
    //   start: event[0],
    //   end: event[1]
    // })),
    //
    // select: function (info) {
    //   function formatDate(date) {
    //     const year = date.substr(0,4);
    //     const month = date.substr(5,2);
    //     const day = date.substr(8,2);
    //     const hours = date.substr(11,2);
    //     const minutes = date.substr(14,2);
    //     const seconds = date.substr(17,2);
    //     return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    //   }
    //
    //   selectedRange = {
    //     start: formatDate(info.startStr),
    //     end: formatDate(info.endStr),
    //   };
    // },
  });
  //document.getElementsByClassName('fc-timegrid-axis-cushion fc-scrollgrid-shrink-cushion fc-scrollgrid-sync-inner').innerText = `Celý deň`;

  return calendar;
}

function renderDetails(car_details) {
  const carDetails = car_details[0];
  car_name = carDetails[1];
  stk = carDetails[8]
  if (carDetails[3] === 'stand_by') {
    carDetails[3] = 'Voľné';
  } else if (carDetails[3] === 'leased') {
    carDetails[3] = 'Obsadené';
  } else if (carDetails[3] === 'service') {
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
  const msg = data['msg'];
  const modalTitle = document.querySelector('#modal .modal-inner h2');
  const modalMessage = document.querySelector('#modal .modal-inner p');
  if (status === true){
    if (msg === 'Request for a private ride was sent!'){
      modalTitle.textContent = 'Čaká sa na potvrdenie...';
      modalMessage.textContent = 'Požiadavka na súkromnú jazdu bola úspešne odoslaná!';
    }else {
      modalTitle.textContent = 'Úspech :)';
      modalMessage.textContent = 'Rezervácia auta bola úspešná!';
    }

  }else{
    modalTitle.textContent = 'Neúspech :(';
    modalMessage.textContent = 'Rezervácia auta sa nepodarila, skúste to znova.';
  }
  modal.classList.add('open');

}

function leaseCar(selectedRange) {
  let recipient = role === "manager" ? document.getElementById('car-renter').value : username;
  is_private = document.getElementById('isPrivate').checked;

  let data = {
    'username': username,
    'recipient': recipient,
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
      console.log(data);
      reload(data);
      fetchCarData(car_id, Token, username, role);

    })
    .catch(error => console.error('Error:', error));
}

function getRoute(start, end, map){
  const key = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImUwZTRmZGQ4ZDQxYjQ4ZjRiNTZjOGVlYzMzNTEzZDM2IiwiaCI6Im11cm11cjY0In0='
  fetch(`https://api.openrouteservice.org/v2/directions/driving-car?api_key=${key}&start=${start['lng']},${start['lat']}&end=${end['lng']},${end['lat']}`, {method: 'GET'})
    .then(response => response.json())
    .then(data => {
      console.log(data['features'][0]['properties']['summary']);
      let infoCard = document.getElementById('route-info');

      let distanceHeader = document.createElement('h2');
      distanceHeader.textContent = 'Vzdialenosť'
      infoCard.appendChild(distanceHeader);

      let distanceData = document.createElement('p');
      distanceData.textContent = Math.round(data['features'][0]['properties']['summary']['distance'] / 1000) + ' km';
      infoCard.appendChild(distanceData);

      let durationHeader = document.createElement('h2');
      durationHeader.textContent = 'Trvanie'
      infoCard.appendChild(durationHeader);

      let durationData = document.createElement('p');
      durationData.textContent = data['features'][0]['properties']['summary']['duration'] / 60 + ' h';
      infoCard.appendChild(durationData);

      geojs = L.geoJSON(data).addTo(map);
  })
}

document.addEventListener('DOMContentLoaded', () => {
  let marker_list = [];
  let coords_list = [];
  let map = L.map('map').setView([48.727103, 19.120248], 13);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  map.on('click', (e) => {
    if (marker_list.length <= 2) {
      marker_list.push(L.marker(e.latlng).addTo(map));
      coords_list.push(e.latlng);
      if (marker_list.length === 2) {
        getRoute(coords_list[0], coords_list[1], map);
      }
    }
    if (marker_list.length > 2) {
      geojs.removeFrom(map);
      for (const marker of marker_list) {
        marker.remove();
      }
      marker_list = [];
      coords_list = [];
    }
  })

  document.getElementById('open-assisted').addEventListener('click', (e) => {
    document.getElementById('choices').style.display = 'none';
    document.getElementById('assisted').style.display = 'block';
    map.invalidateSize();
  })
  document.getElementById('open-manual').addEventListener('click', () => {
    loadCarList();
    document.getElementById('choices').style.display = 'none';
    document.getElementById('manual').style.display = 'block';
  })
  document.getElementById('open-trip').addEventListener('click', () => {
    console.log('open-trip');
    document.getElementById('choices').style.display = 'none';
    document.getElementById('trip').style.display = 'block';
  })
})
