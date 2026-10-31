using Domain.Entities;
using System;
using System.Collections.Generic;
using System.Linq.Expressions;
using System.Text;

namespace Application.Interfaces
{
    public interface IRegistrationRequestService
    {
        Task<Registration_Request?> GetByIdAsync(int id);
        Task<IEnumerable<Registration_Request>> GetAllAsync();
        Task CreateAsync(Registration_Request request);
        Task UpdateAsync(Registration_Request request);
        Task DeleteAsync(int id);
    }
}

