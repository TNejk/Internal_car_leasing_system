const welcomeMessage = document.getElementById('welcome-message');
let email = null;

function get_session_data() {
  fetch('/get_session_data', {method: 'POST'})
    .then(res => res.json())
    .then(data => {
      email = data.username;
      welcomeMessage.innerText = `Vytaj ${email}!`;
    });
}

function renderCalendar(dates) {
  const calendarEl = document.getElementById('calendar');
  const today = new Date(); // Get today's date

  const calendar = new FullCalendar.Calendar(calendarEl, {
    height: 700,
    initialView: 'timeGridMonth',
    locale: 'sk',
    // columnHeaderFormat: { day: 'numeric', month: 'numeric' },
    selectable: true,
    allDayText: 'Celý deň',

    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'timeGridMonth,timeGridWeek,timeGridDay',
    },

    events: dates.map((event) => ({
      title: event.car_name,
      start: event.time_from,
      end: event.time_to,
      color:event.color,
      car_id: event.car_id
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
        dateIncrement: { months: 1 }
      },
      timeGridWeek: {
        buttonText: 'Týždeň'
      },
      timeGridDay: {
        buttonText: 'Deň'
      },
      timeGridToday: {
        buttonText: 'Dnes'
      },
      today: {
        buttonText: 'Dnes'
      }
    },

    customButtons: {
      next: {
        click: function() {
          calendar.next();
          const view = calendar.view;
          const month = view.currentStart.getMonth() + 1;
          get_leases(month);
          calendar.update();
        }
      }
    }

  });

  return calendar;
}

function get_leases(month){
  fetch('/manager/get_monthly_leases', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({'month': month},
      )})
  .then(res => res.json())
  .then(data => {
    console.log(data)
    for (let lease of data){
      lease.color = getRandomColor();
    }
    return data
  })
}

function getRandomColor() {
  var letters = '0123456789ABCDEF';
  var color = '#';
  for (var i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
}

document.addEventListener("DOMContentLoaded", function() {
  get_session_data();
  const month = new Date().getMonth() + 1;
  var data = get_leases(month);
  console.log(data);
  const calendar = renderCalendar(data);
  calendar.render();
  document.getElementsByClassName('fc-timegrid-axis-cushion fc-scrollgrid-shrink-cushion fc-scrollgrid-sync-inner').innerText = `Celý deň`;
});