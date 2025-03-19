const welcomeMessage = document.getElementById('welcome-message');
const modalMonthly = document.getElementById('modal-monthly');
const modalBackdrop = document.getElementById('modal-backdrop');
let email = null;

function get_session_data() {
  fetch('/get_session_data', {method: 'POST'})
    .then(res => res.json())
    .then(data => {
      email = data.username;
      welcomeMessage.innerText = `Vitaj ${email}!`;
    });
}

function showEventDetails(event){
  modalMonthly.innerHTML = '';

  const formatter = new Intl.DateTimeFormat("sk-SK", {
    weekday: "long",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    });

  let from = event.start.toISOString().replace('T', ' '); // Fix format
  let to = event.end.toISOString().replace('T', ' '); // Fix format

  // Convert to Date objects
  from = new Date(from);
  to = new Date(to);

  // Format properly
  from = formatter.format(from);
  to = formatter.format(to);

  from = String(from).charAt(0).toUpperCase() + String(from).slice(1);
  to = String(to).charAt(0).toUpperCase() + String(to).slice(1);


  const modalContent = document.createElement('div');
  modalContent.classList.add('modal-monthly-content');

  const title = document.createElement('h2');
  title.innerHTML = event.title;
  modalContent.appendChild(title);

  const email = document.createElement('h3');
  email.innerHTML = event.extendedProps.driver_email;
  modalContent.appendChild(email);

  const start = document.createElement('p');
  start.innerHTML = from;
  modalContent.appendChild(start);

  const end = document.createElement('p');
  end.innerHTML = to;
  modalContent.appendChild(end);

  const exit = document.createElement('button');
  exit.innerHTML = 'Odísť';
  exit.onclick = function () {
    closeModalF();
  }
  modalContent.appendChild(exit);

  modalMonthly.appendChild(modalContent);
  modalBackdrop.style.display = 'block';
  modalMonthly.style.display = 'block';


}

function renderCalendar(dates) {
  const calendarEl = document.getElementById('calendar');

  const calendar = new FullCalendar.Calendar(calendarEl, {
    height: 750,
    initialView: 'timeGridMonth',
    locale: 'sk',
    selectable: true,
    allDayText: 'Celý deň',
    nowIndicator: true,

    headerToolbar: {
      right: 'timeGridMonth,timeGridWeek,timeGridDay',
    },

    events: dates.map((event) => ({
      title: event[2],
      start: event[0],
      end: event[1],
      extendedProps: {driver_email: event[3]},
      color: event[4]
    })),

    views: {
      timeGridMonth: {
        type: 'timeGrid',
        visibleRange: function(currentDate) {
          const start = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
          const end = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
          return { start, end };
        },
        buttonText: 'Mesiac',
        classNames: ['time-grid-month'],
        dateIncrement: { months: 1 },
        dayHeaderFormat: { day: 'numeric', month: 'numeric' },
      },
      timeGridWeek: {
        buttonText: 'Týždeň'
      },
      timeGridDay: {
        buttonText: 'Deň'
      },
      timeGridToday: {
        buttonText: 'Dnes'
      }
    },

    customButtons: {
      this: {
        buttonText: 'Dnes',
        click: function() {
          calendar.today();
        }
      }
    },

    eventClick: function(info) {
      console.log(info.event.start);
      console.log(info.event.end);
      showEventDetails(info.event);
    }

  });
  document.getElementsByClassName('fc-timegrid-axis-cushion fc-scrollgrid-shrink-cushion fc-scrollgrid-sync-inner').innerText = `Celý deň`;
  document.getElementById('loading-message').style.display = 'none';
  calendar.render();
}

function get_leases(month) {
  fetch('/manager/get_monthly_leases', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({'month': month},
    )
  })
    .then(res => res.json())
    .then(data => {
      for (let lease of data) {
        lease.push(getRandomColor());
        lease[0] = new Date(lease[0]);
        lease[1] = new Date(lease[1]);
      }
      renderCalendar(data);

    })
}

function getRandomColor() {
  const letters = '0123456789ABCDEF';
  let color = '#';
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
}

function closeModalF(){
  modalMonthly.style.display = "none";
  modalBackdrop.style.display = "none";
}

document.addEventListener("DOMContentLoaded", function() {
  get_session_data();
  const currentMonth = new Date().getMonth() + 1;
  get_leases(currentMonth);
});
