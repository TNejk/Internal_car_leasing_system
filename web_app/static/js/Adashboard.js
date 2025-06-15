const carDataInput = document.getElementById("car-data-input");
const userDataInput = document.getElementById("user-data-input");
const addUser = document.getElementById("add-user");
const clearUser = document.getElementById("clear-user");
const addCar = document.getElementById("add-car");
const imageInput = document.getElementById('imageInput');
const preview = document.getElementById('preview');
let reader;

let role;
let requester;
let req_pass;

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
        edit.textContent = 'Uprav'; // corrected this
        edit.addEventListener('click', () => {
          // your edit logic here
          editEntry('car',car[0]);
          console.log('Edit clicked');
        });

        const remove = document.createElement('button');
        remove.classList.add('remove');
        remove.textContent = 'Zmaž';
        remove.addEventListener('click', () => {
          // your delete logic here
          deleteEntry('car',car[0]);
          console.log('Remove clicked');
        });

        buttontd.appendChild(edit);
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
        edit.classList.add('edit');
        edit.textContent = 'Uprav';
        edit.addEventListener('click', () => {
          // your edit logic here
          editEntry('user',user[2]);
          console.log('Edit clicked');
        });

        const remove = document.createElement('button');
        remove.classList.add('remove');
        remove.textContent = 'Zmaž';
        remove.addEventListener('click', () => {
          // your delete logic here
          deleteEntry('user',user[2]);
          console.log('Remove clicked');
        });

        buttontd.appendChild(edit);
        buttontd.appendChild(remove);

        newLine.appendChild(buttontd);

        userDataInput.appendChild(newLine);

      }
  });
}

function editModal(what, id){

}

function editEntry(what, id){
  if (what === 'user'){
    let payload = {'role': role,}
  }
}

function deleteEntry(what, id) {
  if (what === 'user'){
    let payload = {'role': role, 'user': id};
    fetch(`/admin/delete_user`,{method: 'POST',headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),})
      .then(res => res.json()).then(data => {
      console.log(data);
    })
  }else if(what === 'car'){
    let payload = {'role': role, 'car': id};
    fetch(`/admin/delete_car`,{method: 'POST',headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),})
      .then(res => res.json()).then(data => {
      console.log(data);
    })
  }
}

function add_user (){
  let name = document.getElementById('user-name').value;
  let email = document.getElementById('user-email').value;
  let password = document.getElementById('user-password').value;
  let role = document.getElementById('user-role').value;
  let data = {'name': name, 'email': email, 'password': password, 'role': role, 'requester': requester, 'req_password': req_pass};
  fetch('/admin/create_user',{method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)}).then(res => res.json())
    .then(data => {
      console.log(data);
    })
}

function add_car (){
  let name = document.getElementById('car-name').value;
  let type = document.getElementById('car-type').value;
  let gas = document.getElementById('gas-type').value;
  let spz = document.getElementById('plate-number').value;
  let state = document.getElementById('state').value;
  let location = document.getElementById('location').value;
  let drive_tp = document.getElementById('drive-tp').value;
  let data = {'name': name, 'type': type, 'status': state, 'location': location, 'spz': spz, 'gas': gas, 'drive_tp': drive_tp, 'image': reader.result};
  console.log(data);
  fetch('/admin/create_car',{method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)}).then(res => res.json())
    .then(data => {
      console.log(data);
    })
}

addUser.addEventListener('click', function() {
  add_user();
})

addCar.addEventListener('click', function() {
  add_car();
})

clearUser.addEventListener('click', () => {
  document.getElementById('user-name').value = '';
  document.getElementById('user-email').value = '';
  document.getElementById('user-password').value = '';
  document.getElementById('car-name').value = '';
  document.getElementById('plate-number').value = '';

})

imageInput.addEventListener('change', function () {
  const file = this.files[0];
  if (file) {
    reader = new FileReader();

    reader.onload = function (e) {
      preview.src = e.target.result;
    };

    reader.readAsDataURL(file); // converts the image to base64 string
  }
});

function closeModalF(){
  modalLeaseDetails.style.display = "none";
  modalReturnCar.style.display = "none";
  modalBackdrop.style.display = "none";
} // finished


document.addEventListener("DOMContentLoaded", function() {
  get_data();
  fetch('/get_session_data', {method: 'POST'})
  .then(res => res.json())
  .then(data => {
    role = data.role;
    requester = data.username;
    req_pass = data.password;
  })
})