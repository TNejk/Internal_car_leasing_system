// dashboard.js
function showDetails(carId, token) {
    fetch('https://icls.sosit-wh.net/get_full_car_info', { method: 'POST',
                                                           headers: { 'Authorization': 'Bearer ' + token,
                                                                      'Content-Type': 'application/json'
                                                           },
                                                           body: JSON.stringify({'car_id': carId})})
    .then(response => response.json())
    .then(data => {
      cars = data['car_details'];
      dates = data['allowed_details'];
      console.log(cars);
      document.getElementById("car-name").textContent = `Auto - ${cars[2]}`;
      document.getElementById("car-type").textContent = `Typ - ${cars[3]}`;
      document.getElementById("car-status").textContent = `Stav - ${cars[4]}`;
      document.getElementById("car-health").textContent = `Zdravie - ${cars[5]}`;
      document.getElementById("car-frequency").textContent = `Frekvencia obsadenia - ${cars[6]}`;
      document.getElementById("car-location").textContent = `Domáce mesto - ${cars[7]}`;

      // ak existuje image
      if (cars[8]) {
        document.getElementById("car-image").src = cars[8];
        document.getElementById("car-image").alt = `Auto ${cars[2]}`;
      } else {
         // ak nie, tak default image
         document.getElementById("car-image").src = "https://pictures.dealer.com/m/maguirechevrolet/0087/a976281f56ff06d46dc390283aa14da6x.jpg?impolicy=downsize_bkpt&imdensity=1&w=520";
         document.getElementById("car-image").alt = "Auto";
       }

      document.getElementById("car-details").style.display = "block";
      document.getElementById("default-message").style.display = "none";

    })
    .catch(error => console.error('Error fetching car details:', error));
}
