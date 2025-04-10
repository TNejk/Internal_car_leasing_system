const carDataInput = document.getElementById("car-data-input");
const userDataInput = document.getElementById("user-data-input");
const addUser = document.getElementById("add-user");
const clear = document.getElementById("clear");

function get_data() {
  fetch('/admin/get_car_list', {method: 'POST'}).then(res => res.json()).then(data => {
      // [16, 'Wolksvagen Golf', 'personal', 'stand_by', 'good', 1, 'BB', 'https://fl.gamo.sosit-wh.net/wolks.jpg', 'BB676GF', 'BENZÍN', 'AUTOMAT']
      for (let car of data) {

        const newLine = document.createElement('tr')

        const id = document.createElement('td');
        id.textContent = car[0];
        newLine.appendChild(id);

        const name = document.createElement('td');
        name.textContent = car[1];
        newLine.appendChild(name);

        const spz = document.createElement('td');
        spz.textContent = car[8];
        newLine.appendChild(spz);

        const typ = document.createElement('td');
        typ.textContent = car[2];
        newLine.appendChild(typ);

        const palivo = document.createElement('td');
        palivo.textContent = car[9];
        newLine.appendChild(palivo);

        const radenie = document.createElement('td');
        radenie.textContent = car[10];
        newLine.appendChild(radenie);

        const stav = document.createElement('td');
        stav.textContent = car[4];
        newLine.appendChild(stav);

        const status = document.createElement('td');
        status.textContent = car[3];
        newLine.appendChild(status);

        const metrika = document.createElement('td');
        metrika.textContent = car[5];
        newLine.appendChild(metrika);

        const lokacia = document.createElement('td');
        lokacia.textContent = car[6];
        newLine.appendChild(lokacia);

        const buttontd = document.createElement('td');
        const edit = document.createElement('button');
        edit.classList.add('edit');
        edit.innerContent = `Uprav`;
        buttontd.appendChild(edit);

        const remove = document.createElement('button');
        remove.classList.add('remove');
        remove.textContent = `Zmaž`;
        buttontd.appendChild(remove);
        
        newLine.appendChild(buttontd);

        carDataInput.appendChild(newLine);
      }

    });

  fetch('/admin/get_user_list', {method: 'POST'}).then(res => res.json()).then(data => {
      // [6, 'klaudia.priezvisko@gamo.sk', 'manager', 'Klaudia']
      for (let user of data) {

        const newLine = document.createElement('tr')

        const id = document.createElement('td');
        id.textContent = user[0];
        newLine.appendChild(id);

        const name = document.createElement('td');
        name.textContent = user[1];
        newLine.appendChild(name);

        const email = document.createElement('td');
        email.textContent = user[2];
        newLine.appendChild(email);

        const role = document.createElement('td');
        role.textContent = user[3];
        newLine.appendChild(role);

        const buttontd = document.createElement('td');
        const edit = document.createElement('button');
        //edit.onclick();
        buttontd.textContent = `Uprav`;
        buttontd.appendChild(edit);

        const remove = document.createElement('button');
        //remove.onclick();
        remove.textContent = `Zmaž`;
        buttontd.appendChild(remove);

        newLine.appendChild(buttontd);

        userDataInput.appendChild(newLine);

      }
  });
}

// function delete_record(id, what) {
//   if (what === 'use')
//   body = {'id':}
// }

function add_user (){
  let name = document.getElementById('user-name').value;
  let email = document.getElementById('user-email').value;
  let password = document.getElementById('user-password').value;
  let role = document.getElementById('user-role').value;
  console.log(name, email, password, role)

}

addUser.addEventListener('click', function() {
  add_user();
})

clear.addEventListener('click', () => {
  console.log('clear user');
  document.getElementById('user-name').value = '';
  document.getElementById('user-email').value = '';
  document.getElementById('user-password').value = '';
  document.getElementById('user-role').value = '';
})


document.addEventListener("DOMContentLoaded", function() {
  get_data();
})