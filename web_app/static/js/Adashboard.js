const carDataInput = document.getElementById("car-data-input");

function get_data() {
  fetch('/admin/get_car_list', {method: 'POST'}).then(res => res.json())
    .then(data => {
      // [16, 'Wolksvagen Golf', 'personal', 'stand_by', 'good', 1, 'BB', 'https://fl.gamo.sosit-wh.net/wolks.jpg', 'BB676GF', 'BENZÍN', 'AUTOMAT']
      for (let car of data) {
        const id = document.createElement('td');
        id.textContent = car[0];
        carDataInput.appendChild(id);

        const name = document.createElement('td');
        name.textContent = car[1];
        carDataInput.appendChild(name);

        const spz = document.createElement('td');
        spz.textContent = car[8];
        carDataInput.appendChild(spz);

        const typ = document.createElement('td');
        typ.textContent = car[2];
        carDataInput.appendChild(typ);

        const palivo = document.createElement('td');
        palivo.textContent = car[9];
        carDataInput.appendChild(palivo);

        const radenie = document.createElement('td');
        radenie.textContent = car[10];
        carDataInput.appendChild(riadenie);

        const stav = document.createElement('td');
        stav.textContent = car[4];
        carDataInput.appendChild(stav);

        const status = document.createElement('td');
        status.textContent = car[3];
        carDataInput.appendChild(status);

        const metrika = document.createElement('td');
        metrika.textContent = car[5];
        carDataInput.appendChild(metrika);

        const lokacia = document.createElement('td');
        lokacia.textContent = car[6];
        carDataInput.appendChild(lokacia);

        const buttontd = document.createElement('td');
        const edit = document.createElement('button');
        edit.classList.add('edit');
        buttontd.textContent = `Uprav`;
        buttontd.appendChild(edit);

        const remove = document.createElement('button');
        remove.classList.add('remove');
        remove.textContent = `Remove`;
        buttontd.appendChild(remove);
        
        carDataInput.appendChild(buttontd);
      }

    });

  fetch('/admin/get_user_list', {method: 'POST'}).then(res => res.json())
    .then(data => {
      // [6, 'klaudia.priezvisko@gamo.sk', '5cf18799df63f64e0aa0f79271cd78b5c8c6c4bf9b69c19798c8abcc242946fd', 'manager', 'Klaudia']

    });
}


document.addEventListener("DOMContentLoaded", function() {
  get_data();
})