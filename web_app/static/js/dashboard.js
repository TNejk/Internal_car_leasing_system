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
        classNames: ['time-grid-month']
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
  });

  return calendar;
}

function get_leases(){
  const month = new Date().getMonth() + 1;
  console.log(month);
  fetch('/manager/get_monthly_leases', {method: 'POST', body: JSON.stringify({ month:  month})})
  .then(res => res.json())
  .then(data => {
    console.log(data)
    for (let lease of data){
      lease.color = getRandomColor();
    }
    console.log(JSON.stringify(data, null, 2));
    const calendar = renderCalendar(data);
    console.log('render calendar');
    calendar.render();
    document.getElementsByClassName('fc-timegrid-axis-cushion fc-scrollgrid-shrink-cushion fc-scrollgrid-sync-inner').innerText = `Celý deň`;
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
  console.log('get data')
  get_session_data();
  console.log('get leases');
  get_leases();
  console.log('done');
});