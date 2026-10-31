using Application.Interfaces;
using Domain.Entities;
using System;
using System.Collections.Generic;
using System.Text;

namespace Application.Services
{

    public class RegistrationRequestService : IRegistrationRequestService
    {
        public Task CreateAsync(Registration_Request request)
        {
            throw new NotImplementedException();
        }

        public Task DeleteAsync(int id)
        {
            throw new NotImplementedException();
        }

        public Task<IEnumerable<Registration_Request>> GetAllAsync()
        {
            throw new NotImplementedException();
        }

        public Task<Registration_Request?> GetByIdAsync(int id)
        {
            throw new NotImplementedException();
        }

        public Task UpdateAsync(Registration_Request request)
        {
            throw new NotImplementedException();
        }
    }
}
