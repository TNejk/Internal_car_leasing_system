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

async function renderCalendar() {
  const calendarEl = document.getElementById('calendar');

  let month = new Date().getMonth() + 1;
  let dates = await get_leases(month);

  const calendar = new FullCalendar.Calendar(calendarEl, {
    height: 700,
    initialView: 'timeGridMonth',
    locale: 'sk',
    selectable: true,
    allDayText: 'Celý deň',
    nowIndicator: true,

    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'timeGridMonth,timeGridWeek,timeGridDay',
    },

    events: dates.map((event) => ({
      title: event[3],
      start: event[0],
      end: event[1],
      extendedProps: {car_id: event[2]},
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
        columnHeaderFormat: { day: 'numeric', month: 'numeric' },
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
      },
      next: {
        click: function() {
          calendar.next();
          const view = calendar.view;
          const month = view.currentStart.getMonth() + 1;
          get_leases(month);
        }
      }
    }

  });
  document.getElementsByClassName('fc-timegrid-axis-cushion fc-scrollgrid-shrink-cushion fc-scrollgrid-sync-inner').innerText = `Celý deň`;
  console.log('kalendar renderovany');
  calendar.render();
}

async function get_leases(month) {
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
        lease[0] = new Date(lease[0]).toISOString().replace('.000Z', '').replace('T', ' ');
        lease[1] = new Date(lease[1]).toISOString().replace('.000Z', '').replace('T', ' ');
      }
      console.log('fetchnute data ready na return do renderCalendar')
      console.log(data);
      return data;
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

document.addEventListener("DOMContentLoaded", function() {
  get_session_data();
  renderCalendar();
});